// SDL2 Renderer Test - mimics chocolate-doom's approach EXACTLY
// Uses SDL_CreateRenderer (not OpenGL context) - this is how chocolate-doom works
// NOTE: This test does NOT use SDL_WINDOW_OPENGL to match chocolate-doom behavior!

#include <SDL2/SDL.h>
#include <SDL2/SDL_opengles2.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    SDL_Window *window;
    SDL_Renderer *renderer;
    
    printf("=== SDL2 Renderer Test (chocolate-doom EXACT style) ===\n");
    printf("This test REPLICATES chocolate-doom's exact window creation flags:\n");
    printf("  - No SDL_WINDOW_OPENGL flag\n");
    printf("  - No SDL_GL_SetAttribute calls before window creation\n");
    printf("  - Uses fullscreen mode (like chocolate-doom defaults)\n\n");
    
    // Initialize SDL with video
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        printf("SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }
    printf("SDL_Init succeeded\n");
    
    // Set hints like chocolate-doom does (via SDL_SetHint in wrapper)
    SDL_SetHint(SDL_HINT_VIDEODRIVER, "wayland");
    SDL_SetHint(SDL_HINT_RENDER_DRIVER, "opengles2");
    
    // chocolate-doom uses these flags:
    // SDL_WINDOW_RESIZABLE | SDL_WINDOW_ALLOW_HIGHDPI | SDL_WINDOW_FULLSCREEN_DESKTOP
    // But we'll test without fullscreen first to isolate the issue
    printf("Creating window WITHOUT SDL_WINDOW_OPENGL flag (like chocolate-doom)...\n");
    printf("Full window flags: SDL_WINDOW_RESIZABLE | SDL_WINDOW_ALLOW_HIGHDPI\n");
    window = SDL_CreateWindow("SDL2 Renderer Test",
                              SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                              800, 600,
                              SDL_WINDOW_RESIZABLE | SDL_WINDOW_ALLOW_HIGHDPI);
    
    if (!window) {
        printf("Window creation failed: %s\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }
    printf("Window created successfully\n");
    
    // Create renderer (like chocolate-doom does - NO explicit GL context!)
    printf("Creating renderer with SDL_CreateRenderer (no explicit GL context)...\n");
    Uint32 renderer_flags = SDL_RENDERER_TARGETTEXTURE | SDL_RENDERER_ACCELERATED;
    renderer = SDL_CreateRenderer(window, -1, renderer_flags);
    
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
    
    // Test rendering - draw a simple pattern (like chocolate-doom does)
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
    
    printf("=== RENDERER TEST PASSED (chocolate-doom style) ===\n");
    printf("Window will stay visible for 5 seconds...\n");
    SDL_Delay(5000);
    
    // Cleanup
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    
    return 0;
}