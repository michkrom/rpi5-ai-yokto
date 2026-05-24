// Test SDL2 initialization like chocolate-doom does
#include <SDL2/SDL.h>
#include <SDL2/SDL_opengles2.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    printf("=== SDL2 Window Init Test (chocolate-doom style) ===\n");
    
    // Check SDL2 version
    printf("SDL2 version: %s\n", SDL_GetRevision());
    
    // Initialize SDL2 with video only (like chocolate-doom)
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        printf("SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }
    printf("SDL_Init(VIDEO) succeeded\n");
    
    // Set OpenGL ES 2.0 context attributes BEFORE creating window
    printf("Setting OpenGL ES 2.0 context attributes...\n");
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);
    
    // Set environment hints like chocolate-doom might
    SDL_SetHint(SDL_HINT_VIDEODRIVER, "wayland");
    SDL_SetHint(SDL_HINT_RENDER_DRIVER, "opengles2");
    
    // Create window with OpenGL ES 2.0 context (chocolate-doom style)
    printf("Creating window with OpenGL ES 2.0...\n");
    SDL_Window *window = SDL_CreateWindow(
        "Test Window",
        SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED,
        640, 480,
        SDL_WINDOW_OPENGL | SDL_WINDOW_SHOWN
    );
    
    if (!window) {
        printf("Window creation failed: %s\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }
    printf("Window created successfully\n");
    
    // Create OpenGL ES 2.0 context
    printf("Creating OpenGL ES 2.0 context...\n");
    
    SDL_GLContext gl_context = SDL_GL_CreateContext(window);
    if (!gl_context) {
        printf("GL context creation failed: %s\n", SDL_GetError());
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    printf("GL context created successfully\n");
    
    // Clear screen to show it works
    glClearColor(0.2f, 0.4f, 0.8f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
    SDL_GL_SwapWindow(window);
    
    printf("=== ALL TESTS PASSED ===\n");
    printf("Window will stay visible for 5 seconds...\n");
    SDL_Delay(5000);
    
    // Cleanup
    SDL_GL_DeleteContext(gl_context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    
    return 0;
}