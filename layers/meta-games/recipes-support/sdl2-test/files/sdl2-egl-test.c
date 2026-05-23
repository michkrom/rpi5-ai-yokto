// Simple SDL2 EGL test - verifies EGL initialization works with SDL2
// This is a minimal test to verify the SDL2 + OpenGL ES + Wayland/Mesa stack

#include <SDL2/SDL.h>
#include <GLES2/gl2.h>
#include <stdio.h>
#include <math.h>

int main(int argc, char *argv[]) {
    SDL_Window *window;
    SDL_GLContext context;
    
    printf("=== SDL2 EGL Test ===\n");
    
    // Initialize SDL with video and events subsystems
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }
    
    printf("SDL_Init succeeded\n");
    
    // Set OpenGL ES 2.0 context
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);
    
    // Create window
    window = SDL_CreateWindow("SDL2 EGL Test",
                              SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                              640, 480,
                              SDL_WINDOW_OPENGL | SDL_WINDOW_SHOWN);
    if (!window) {
        fprintf(stderr, "Window could not be created! SDL_Error: %s\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }
    printf("Window created successfully\n");
    
    // Create OpenGL context
    context = SDL_GL_CreateContext(window);
    if (!context) {
        fprintf(stderr, "OpenGL context could not be created! SDL_Error: %s\n", SDL_GetError());
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    printf("OpenGL context created\n");
    
    // Clear screen with a color
    glClearColor(0.2f, 0.4f, 0.8f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
    
    // Swap buffers to display
    SDL_GL_SwapWindow(window);
    
    printf("=== ALL TESTS PASSED ===\n");
    
    // Cleanup
    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    
    return 0;
}