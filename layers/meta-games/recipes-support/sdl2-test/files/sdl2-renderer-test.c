// SDL2 Renderer Test - mimics chocolate-doom's approach
// Uses SDL_CreateRenderer (not OpenGL context) - this is how chocolate-doom works

#include <SDL2/SDL.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    SDL_Window *window;
    SDL_Renderer *renderer;
    
    printf("=== SDL2 Renderer Test (chocolate-doom style) ===\n");
    
    // Initialize SDL with video
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        printf("SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }
    printf("SDL_Init succeeded\n");
    
    // Set hints like chocolate-doom does
    SDL_SetHint(SDL_HINT_VIDEODRIVER, "wayland");
    
    // Create window (no SDL_WINDOW_OPENGL flag - using renderer API)
    printf("Creating window with SDL_CreateWindow...\n");
    window = SDL_CreateWindow("SDL2 Renderer Test",
                              SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                              640, 480,
                              SDL_WINDOW_RESIZABLE | SDL_WINDOW_SHOWN);
    
    if (!window) {
        printf("Window creation failed: %s\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }
    printf("Window created successfully\n");
    
    // Create renderer (like chocolate-doom does)
    printf("Creating renderer with SDL_CreateRenderer...\n");
    renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);
    
    if (!renderer) {
        printf("Renderer creation failed, trying software fallback...\n");
        renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_SOFTWARE);
    }
    
    if (!renderer) {
        printf("Renderer creation failed: %s\n", SDL_GetError());
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    printf("Renderer created successfully\n");
    
    // Test rendering - draw a simple pattern
    printf("Testing rendering...\n");
    
    // Set draw color to blue (like doom's status bar)
    SDL_SetRenderDrawColor(renderer, 0, 0, 255, 255);
    SDL_RenderClear(renderer);
    
    // Draw a green rectangle (like health/ammo numbers)
    SDL_SetRenderDrawColor(renderer, 0, 255, 0, 255);
    SDL_Rect rect = {100, 100, 200, 100};
    SDL_RenderFillRect(renderer, &rect);
    
    // Present to screen
    SDL_RenderPresent(renderer);
    
    printf("=== RENDERER TEST PASSED ===\n");
    printf("Window will stay visible for 5 seconds...\n");
    SDL_Delay(5000);
    
    // Cleanup
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    
    return 0;
}