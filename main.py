import pygame
import sys
import math
import random
from collections import deque

# Initialize pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 1000, 700
BACKGROUND_COLOR = (240, 240, 240)
VERTEX_RADIUS = 20
EDGE_COLOR = (50, 50, 50)
VERTEX_BORDER_COLOR = (0, 0, 0)
VERTEX_COLORS = [(200, 50, 50), (50, 200, 50), (50, 50, 200), (200, 200, 50)]
TEXT_COLOR = (255, 255, 255)
BUTTON_COLOR = (100, 100, 200)
BUTTON_HOVER_COLOR = (120, 120, 220)
BUTTON_TEXT_COLOR = (255, 255, 255)
PERIPHERY_COLOR = (200, 200, 255, 100)

# Setup display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Planar Triangulated Graph Visualizer")
clock = pygame.time.Clock()
font = pygame.font.SysFont('Arial', 16)

class Vertex:
    def __init__(self, index, x, y, color_idx=0):
        self.index = index
        self.x = x
        self.y = y
        self.color_idx = color_idx
        self.radius = VERTEX_RADIUS
        self.neighbors = set()
    
    def draw(self, screen, show_index=True):
        # Draw the vertex
        color = VERTEX_COLORS[self.color_idx % len(VERTEX_COLORS)]
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, VERTEX_BORDER_COLOR, (int(self.x), int(self.y)), self.radius, 2)
        
        # Draw the index or color indicator
        if show_index:
            text = font.render(str(self.index), True, TEXT_COLOR)
        else:
            text = font.render(str(self.color_idx), True, TEXT_COLOR)
        text_rect = text.get_rect(center=(self.x, self.y))
        screen.blit(text, text_rect)
    
    def distance_to(self, x, y):
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)
    
    def is_inside(self, x, y):
        return self.distance_to(x, y) <= self.radius

class Edge:
    def __init__(self, v1, v2):
        self.v1 = v1
        self.v2 = v2
    
    def draw(self, screen):
        pygame.draw.line(screen, EDGE_COLOR, (self.v1.x, self.v1.y), (self.v2.x, self.v2.y), 2)

class Button:
    def __init__(self, x, y, width, height, text, action):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.hovered = False
    
    def draw(self, screen):
        color = BUTTON_HOVER_COLOR if self.hovered else BUTTON_COLOR
        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        pygame.draw.rect(screen, (50, 50, 50), self.rect, 2, border_radius=5)
        
        text_surface = font.render(self.text, True, BUTTON_TEXT_COLOR)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
    
    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)
        return self.hovered
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovered:
            self.action()
            return True
        return False

class Graph:
    def __init__(self):
        self.vertices = []
        self.edges = set()
        self.periphery = []  # List of vertices on the periphery in order
        self.zoom_level = 1.0
        self.offset_x, self.offset_y = 0, 0
        self.dragging = False
        self.last_mouse_x, self.last_mouse_y = 0, 0
        self.show_indices = True
        self.max_vertex = float('inf')  # For Gm command
        self.selected_vertices = []  # For vertex selection
        self.mode = None  # 'select_vp', 'select_vq', etc.
    
    def add_vertex(self, x, y, color_idx=0):
        # Adjust for zoom and offset
        adj_x = (x - self.offset_x) / self.zoom_level
        adj_y = (y - self.offset_y) / self.zoom_level
        
        # Calculate radius based on expected index size
        radius = VERTEX_RADIUS + min(10, len(self.vertices) // 100)
        new_vertex = Vertex(len(self.vertices) + 1, adj_x, adj_y, color_idx)
        new_vertex.radius = radius
        self.vertices.append(new_vertex)
        return new_vertex
    
    def add_edge(self, v1, v2):
        if v1 != v2 and v2 not in v1.neighbors:
            v1.neighbors.add(v2)
            v2.neighbors.add(v1)
            self.edges.add((min(v1.index, v2.index), max(v1.index, v2.index)))
    
    def start_basic_graph(self):
        self.vertices = []
        self.edges = set()
        self.periphery = []
        
        # Create initial triangle
        center_x, center_y = WIDTH / (2 * self.zoom_level), HEIGHT / (2 * self.zoom_level)
        v1 = self.add_vertex(center_x - 100, center_y - 50, 0)
        v2 = self.add_vertex(center_x + 100, center_y - 50, 1)
        v3 = self.add_vertex(center_x, center_y + 100, 2)
        
        # Add edges
        self.add_edge(v1, v2)
        self.add_edge(v2, v3)
        self.add_edge(v3, v1)
        
        # Set periphery
        self.periphery = [v1, v2, v3]
        self.max_vertex = float('inf')
    
    def find_periphery(self):
        """Find the periphery of the graph using BFS from the leftmost vertex"""
        if not self.vertices:
            return []
        
        # Find leftmost vertex
        leftmost = min(self.vertices, key=lambda v: v.x)
        
        # Use a modified gift wrapping algorithm to find the convex hull
        hull = []
        point_on_hull = leftmost
        i = 0
        
        while True:
            hull.append(point_on_hull)
            endpoint = self.vertices[0]  # Start with first vertex
            
            for j in range(1, len(self.vertices)):
                if endpoint == point_on_hull or self.is_left(point_on_hull, endpoint, self.vertices[j]):
                    endpoint = self.vertices[j]
            
            point_on_hull = endpoint
            
            # Check if we've completed the hull
            if endpoint == hull[0]:
                break
            
            # Safety check to prevent infinite loops
            i += 1
            if i > len(self.vertices):
                break
        
        return hull
    
    def is_left(self, a, b, c):
        """Check if point c is to the left of line a-b"""
        return ((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)) > 0
    
    def add_vertex_to_periphery(self, vp, vq):
        """Add a new vertex connected to all vertices between vp and vq on the periphery"""
        if vp not in self.periphery or vq not in self.periphery:
            return None
        
        # Find indices of vp and vq in periphery
        try:
            idx_p = self.periphery.index(vp)
            idx_q = self.periphery.index(vq)
        except ValueError:
            return None
        
        # Determine the vertices to connect to
        if idx_p < idx_q:
            connect_vertices = self.periphery[idx_p:idx_q+1]
        else:
            connect_vertices = self.periphery[idx_p:] + self.periphery[:idx_q+1]
        
        # Calculate position for new vertex (outside the periphery)
        # Use the centroid of the connecting vertices, then push outward
        cx = sum(v.x for v in connect_vertices) / len(connect_vertices)
        cy = sum(v.y for v in connect_vertices) / len(connect_vertices)
        
        # Find a normal vector to push the point outward
        if len(connect_vertices) >= 2:
            # Use the first and last vertices to determine direction
            v1 = connect_vertices[0]
            v2 = connect_vertices[-1]
            
            # Calculate midpoint of the arc
            mid_x = (v1.x + v2.x) / 2
            mid_y = (v1.y + v2.y) / 2
            
            # Vector from center to midpoint
            dx, dy = mid_x - cx, mid_y - cy
            
            # Normalize and scale
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                dx, dy = dx/length * 100, dy/length * 100
            else:
                dx, dy = 0, 100
        else:
            dx, dy = 0, 100
        
        new_x = cx + dx
        new_y = cy + dy
        
        # Create new vertex
        new_vertex = self.add_vertex(new_x, new_y, random.randint(0, len(VERTEX_COLORS)-1))
        
        # Add edges to all connecting vertices
        for vertex in connect_vertices:
            self.add_edge(new_vertex, vertex)
        
        # Update periphery
        self.update_periphery_after_addition(connect_vertices, new_vertex)
        
        return new_vertex
    
    def update_periphery_after_addition(self, connect_vertices, new_vertex):
        """Update the periphery after adding a new vertex"""
        if not connect_vertices:
            return
        
        # Find the segment in the periphery that we're replacing
        start_idx = self.periphery.index(connect_vertices[0])
        end_idx = self.periphery.index(connect_vertices[-1])
        
        # Replace the segment with the new vertex
        if start_idx <= end_idx:
            self.periphery = self.periphery[:start_idx] + [new_vertex] + self.periphery[end_idx+1:]
        else:
            # Handle wrap-around case
            self.periphery = self.periphery[end_idx+1:start_idx] + [new_vertex]
    
    def add_random_vertex(self):
        """Add a random vertex to the periphery"""
        if len(self.periphery) < 2:
            return
        
        # Select two random vertices from the periphery
        idx1 = random.randint(0, len(self.periphery) - 1)
        idx2 = random.randint(0, len(self.periphery) - 1)
        
        # Ensure they're different and we have at least one vertex between them
        while abs(idx1 - idx2) < 2:
            idx2 = random.randint(0, len(self.periphery) - 1)
        
        vp = self.periphery[min(idx1, idx2)]
        vq = self.periphery[max(idx1, idx2)]
        
        self.add_vertex_to_periphery(vp, vq)
    
    def go_to_vertex(self, m):
        """Hide vertices with index > m"""
        self.max_vertex = m
    
    def draw(self, screen):
        # Draw edges
        for edge in self.edges:
            i1, i2 = edge
            if i1 <= self.max_vertex and i2 <= self.max_vertex:
                v1 = self.vertices[i1-1]
                v2 = self.vertices[i2-1]
                start_x = v1.x * self.zoom_level + self.offset_x
                start_y = v1.y * self.zoom_level + self.offset_y
                end_x = v2.x * self.zoom_level + self.offset_y
                end_y = v2.y * self.zoom_level + self.offset_y
                pygame.draw.line(screen, EDGE_COLOR, (start_x, start_y), (end_x, end_y), 2)
        
        # Draw vertices
        for vertex in self.vertices:
            if vertex.index <= self.max_vertex:
                draw_x = vertex.x * self.zoom_level + self.offset_x
                draw_y = vertex.y * self.zoom_level + self.offset_y
                draw_radius = vertex.radius * self.zoom_level
                
                # Draw vertex
                color = VERTEX_COLORS[vertex.color_idx % len(VERTEX_COLORS)]
                pygame.draw.circle(screen, color, (int(draw_x), int(draw_y)), int(draw_radius))
                pygame.draw.circle(screen, VERTEX_BORDER_COLOR, (int(draw_x), int(draw_y)), int(draw_radius), 2)
                
                # Draw text
                if self.show_indices:
                    text = font.render(str(vertex.index), True, TEXT_COLOR)
                else:
                    text = font.render(str(vertex.color_idx), True, TEXT_COLOR)
                text_rect = text.get_rect(center=(draw_x, draw_y))
                screen.blit(text, text_rect)
        
        # Highlight selected vertices
        for vertex in self.selected_vertices:
            draw_x = vertex.x * self.zoom_level + self.offset_x
            draw_y = vertex.y * self.zoom_level + self.offset_y
            draw_radius = vertex.radius * self.zoom_level + 5
            pygame.draw.circle(screen, (255, 255, 0), (int(draw_x), int(draw_y)), int(draw_radius), 3)
        
        # Draw periphery
        if self.periphery:
            points = []
            for vertex in self.periphery:
                if vertex.index <= self.max_vertex:
                    draw_x = vertex.x * self.zoom_level + self.offset_x
                    draw_y = vertex.y * self.zoom_level + self.offset_y
                    points.append((draw_x, draw_y))
            
            if len(points) > 2:
                # Draw a semi-transparent polygon for the periphery
                pygame.draw.polygon(screen, PERIPHERY_COLOR, points)
                # Draw the periphery outline
                for i in range(len(points)):
                    pygame.draw.line(screen, (100, 100, 200), points[i], points[(i+1) % len(points)], 2)
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                # Check if clicking on a vertex
                mouse_x, mouse_y = pygame.mouse.get_pos()
                for vertex in self.vertices:
                    if vertex.index <= self.max_vertex:
                        draw_x = vertex.x * self.zoom_level + self.offset_x
                        draw_y = vertex.y * self.zoom_level + self.offset_y
                        draw_radius = vertex.radius * self.zoom_level
                        
                        if math.sqrt((draw_x - mouse_x)**2 + (draw_y - mouse_y)**2) <= draw_radius:
                            if self.mode == 'select_vp':
                                self.selected_vertices = [vertex]
                                self.mode = 'select_vq'
                                return True
                            elif self.mode == 'select_vq':
                                if self.selected_vertices and self.selected_vertices[0] != vertex:
                                    self.selected_vertices.append(vertex)
                                    self.add_vertex_to_periphery(self.selected_vertices[0], vertex)
                                    self.selected_vertices = []
                                    self.mode = None
                                    return True
                            break
                
                # Start dragging
                self.dragging = True
                self.last_mouse_x, self.last_mouse_y = mouse_x, mouse_y
                
            elif event.button == 4:  # Scroll up
                self.zoom_level *= 1.1
                # Adjust offset to zoom toward mouse position
                mouse_x, mouse_y = pygame.mouse.get_pos()
                self.offset_x = mouse_x - (mouse_x - self.offset_x) * 1.1
                self.offset_y = mouse_y - (mouse_y - self.offset_y) * 1.1
                
            elif event.button == 5:  # Scroll down
                self.zoom_level /= 1.1
                # Adjust offset to zoom toward mouse position
                mouse_x, mouse_y = pygame.mouse.get_pos()
                self.offset_x = mouse_x - (mouse_x - self.offset_x) / 1.1
                self.offset_y = mouse_y - (mouse_y - self.offset_y) / 1.1
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left click release
                self.dragging = False
        
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                dx = mouse_x - self.last_mouse_x
                dy = mouse_y - self.last_mouse_y
                self.offset_x += dx
                self.offset_y += dy
                self.last_mouse_x, self.last_mouse_y = mouse_x, mouse_y
        
        return False

def main():
    graph = Graph()
    graph.start_basic_graph()
    
    # Create buttons
    buttons = [
        Button(10, 10, 120, 30, "Start (S)", graph.start_basic_graph),
        Button(10, 50, 120, 30, "Random Vertex (R)", graph.add_random_vertex),
        Button(10, 90, 120, 30, "Add Vertex (A)", lambda: setattr(graph, 'mode', 'select_vp')),
        Button(10, 130, 120, 30, "Toggle Index/Color (T)", lambda: setattr(graph, 'show_indices', not graph.show_indices)),
        Button(10, 170, 120, 30, "Center (C)", lambda: setattr(graph, 'offset_x', 0) or setattr(graph, 'offset_y', 0) or setattr(graph, 'zoom_level', 1.0)),
        Button(10, 210, 120, 30, "Zoom In (Z+)", lambda: setattr(graph, 'zoom_level', graph.zoom_level * 1.1)),
        Button(10, 250, 120, 30, "Zoom Out (Z-)", lambda: setattr(graph, 'zoom_level', graph.zoom_level / 1.1)),
    ]
    
    # For Gm command, we'll handle it through keyboard input
    
    running = True
    while running:
        screen.fill(BACKGROUND_COLOR)
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    graph.start_basic_graph()
                elif event.key == pygame.K_r:
                    graph.add_random_vertex()
                elif event.key == pygame.K_a:
                    graph.mode = 'select_vp'
                elif event.key == pygame.K_t:
                    graph.show_indices = not graph.show_indices
                elif event.key == pygame.K_c:
                    graph.offset_x, graph.offset_y = 0, 0
                    graph.zoom_level = 1.0
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:  # Zoom in
                    graph.zoom_level *= 1.1
                elif event.key == pygame.K_MINUS:  # Zoom out
                    graph.zoom_level /= 1.1
                elif event.key == pygame.K_g:
                    # For Gm command, we'd need to parse the number
                    # This is a simplified version
                    try:
                        m = int(input("Enter vertex index to go to: "))
                        graph.go_to_vertex(m)
                    except:
                        pass
            
            # Handle graph events
            graph.handle_event(event)
            
            # Handle button events
            mouse_pos = pygame.mouse.get_pos()
            for button in buttons:
                button.check_hover(mouse_pos)
                button.handle_event(event)
        
        # Draw graph
        graph.draw(screen)
        
        # Draw buttons
        for button in buttons:
            button.draw(screen)
        
        # Draw mode indicator
        if graph.mode:
            mode_text = font.render(f"Mode: {graph.mode}", True, (0, 0, 0))
            screen.blit(mode_text, (WIDTH - 150, 10))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
