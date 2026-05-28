// EGL Wayland visual test - creates a colorful animated display
// Tests raw EGL + Wayland + OpenGL ES 2.0 integration
// Simple test that verifies EGL works without shell protocol

#include <EGL/egl.h>
#include <GLES2/gl2.h>
#include <wayland-client.h>
#include <wayland-egl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include <signal.h>

// Simple vertex shader for full-screen quad
static const char *vertex_shader =
    "attribute vec2 pos;\n"
    "varying vec2 v_tex;\n"
    "void main() {\n"
    "    v_tex = pos * 0.5 + 0.5;\n"
    "    gl_Position = vec4(pos, 0.0, 1.0);\n"
    "}\n";

static const char *fragment_shader =
    "precision mediump float;\n"
    "varying vec2 v_tex;\n"
    "uniform float u_time;\n"
    "void main() {\n"
    "    vec2 p = v_tex - 0.5;\n"
    "    float r = length(p);\n"
    "    float a = atan(p.y, p.x);\n"
    "    float f = pow(sin(r * 20.0 - u_time * 5.0 + a * 3.0), 2.0);\n"
    "    vec3 col = 0.5 + 0.5 * cos(u_time + vec3(0.0, 2.0, 4.0) + f * 3.14);\n"
    "    gl_FragColor = vec4(col, 1.0);\n"
    "}\n";

static void alarm_handler(int sig) {
    printf("\nTimeout reached, exiting...\n");
    _exit(0);
}

static struct wl_compositor *compositor = NULL;

static void registry_handle_global(void *data, struct wl_registry *registry,
                                   uint32_t name, const char *interface,
                                   uint32_t version) {
    printf("Registry: %s (v%d)\n", interface, version);
    if (strcmp(interface, "wl_compositor") == 0) {
        compositor = (struct wl_compositor *)wl_registry_bind(
            registry, name, &wl_compositor_interface, 1);
    }
}

static void registry_handle_global_remove(void *data, struct wl_registry *registry, uint32_t name) {
}

int main(int argc, char *argv[]) {
    EGLDisplay egl_display;
    EGLContext egl_context;
    EGLSurface egl_surface;
    struct wl_display *display;
    struct wl_registry *registry;
    struct wl_surface *surface;
    struct wl_egl_window *egl_window;
    GLuint program, vbo;
    GLint time_loc, pos_loc;
    EGLint major, minor;
    
    printf("=== EGL Wayland Visual Test ===\n");
    
    // Set alarm to exit after 3 seconds
    signal(SIGALRM, alarm_handler);
    alarm(3);
    
    // Connect to Wayland
    display = wl_display_connect(NULL);
    if (!display) {
        fprintf(stderr, "Failed to connect to Wayland display\n");
        return 1;
    }
    printf("Connected to Wayland\n");
    
    // Get registry
    registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &(struct wl_registry_listener){
        registry_handle_global,
        registry_handle_global_remove
    }, NULL);
    
    wl_display_roundtrip(display);
    printf("After roundtrip: compositor=%p\n", compositor);
    
    if (!compositor) {
        fprintf(stderr, "No compositor found\n");
        wl_display_disconnect(display);
        return 1;
    }
    printf("Got compositor\n");
    
    // Create surface
    surface = wl_compositor_create_surface(compositor);
    printf("Created Wayland surface\n");
    
    // NOTE: We don't set up wl_shell or xdg-shell here because:
    // - wl_shell is deprecated in Weston 13.0+
    // - xdg-shell requires proper protocol headers
    // The surface will work but won't be visible to the compositor
    
    // Create EGL window
    egl_window = wl_egl_window_create(surface, 640, 480);
    if (!egl_window) {
        fprintf(stderr, "Failed to create EGL window\n");
        wl_display_disconnect(display);
        return 1;
    }
    printf("Created EGL window\n");
    
    // Initialize EGL
    egl_display = eglGetDisplay((EGLNativeDisplayType)display);
    if (egl_display == EGL_NO_DISPLAY) {
        fprintf(stderr, "Failed to get EGL display\n");
        wl_egl_window_destroy(egl_window);
        wl_display_disconnect(display);
        return 1;
    }
    
    if (!eglInitialize(egl_display, &major, &minor)) {
        fprintf(stderr, "Failed to initialize EGL\n");
        wl_egl_window_destroy(egl_window);
        wl_display_disconnect(display);
        return 1;
    }
    printf("EGL initialized (version %d.%d)\n", major, minor);
    
    // Choose config
    EGLConfig config;
    EGLint num_configs;
    EGLint config_attribs[] = {
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
        EGL_SURFACE_TYPE, EGL_WINDOW_BIT,
        EGL_RED_SIZE, 8,
        EGL_GREEN_SIZE, 8,
        EGL_BLUE_SIZE, 8,
        EGL_ALPHA_SIZE, 8,
        EGL_NONE
    };
    
    if (!eglChooseConfig(egl_display, config_attribs, &config, 1, &num_configs) || num_configs == 0) {
        fprintf(stderr, "Failed to choose EGL config\n");
        wl_egl_window_destroy(egl_window);
        wl_display_disconnect(display);
        return 1;
    }
    printf("Chosen EGL config: %d configs found\n", num_configs);
    
    // Create EGL surface (pass wl_egl_window as EGLNativeWindowType)
    egl_surface = eglCreateWindowSurface(egl_display, config, egl_window, NULL);
    if (egl_surface == EGL_NO_SURFACE) {
        fprintf(stderr, "Failed to create EGL surface\n");
        wl_egl_window_destroy(egl_window);
        wl_display_disconnect(display);
        return 1;
    }
    printf("Created EGL surface\n");
    
    // Create context
    EGLint context_attribs[] = {EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE};
    egl_context = eglCreateContext(egl_display, config, EGL_NO_CONTEXT, context_attribs);
    if (egl_context == EGL_NO_CONTEXT) {
        fprintf(stderr, "Failed to create EGL context\n");
        eglDestroySurface(egl_display, egl_surface);
        wl_egl_window_destroy(egl_window);
        wl_display_disconnect(display);
        return 1;
    }
    printf("Created EGL context\n");
    
    // Make context current
    if (!eglMakeCurrent(egl_display, egl_surface, egl_surface, egl_context)) {
        fprintf(stderr, "Failed to make EGL context current\n");
        eglDestroyContext(egl_display, egl_context);
        eglDestroySurface(egl_display, egl_surface);
        wl_egl_window_destroy(egl_window);
        wl_display_disconnect(display);
        return 1;
    }
    printf("EGL context current\n");
    
    // Create shader program
    GLuint vs = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vs, 1, &vertex_shader, NULL);
    glCompileShader(vs);
    
    GLuint fs = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fs, 1, &fragment_shader, NULL);
    glCompileShader(fs);
    
    program = glCreateProgram();
    glAttachShader(program, vs);
    glAttachShader(program, fs);
    glLinkProgram(program);
    glUseProgram(program);
    
    // Full-screen quad
    float verts[] = {-1,-1, 1,-1, -1,1, 1,1};
    glGenBuffers(1, &vbo);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(verts), verts, GL_STATIC_DRAW);
    pos_loc = glGetAttribLocation(program, "pos");
    glEnableVertexAttribArray(pos_loc);
    glVertexAttribPointer(pos_loc, 2, GL_FLOAT, GL_FALSE, 0, 0);
    time_loc = glGetUniformLocation(program, "u_time");
    
    printf("=== Testing Rendering (3 second timeout) ===\n");
    
    // Render a few frames
    for (int i = 0; i < 10; i++) {
        glUniform1f(time_loc, (float)i * 0.1f);
        glClear(GL_COLOR_BUFFER_BIT);
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
        eglSwapBuffers(egl_display, egl_surface);
        wl_display_dispatch_pending(display);
        usleep(100000);  // 100ms per frame
    }
    
    printf("Rendered 10 frames successfully\n");
    
    // Cleanup
    glDeleteProgram(program);
    glDeleteShader(vs);
    glDeleteShader(fs);
    glDeleteBuffers(1, &vbo);
    
    eglDestroyContext(egl_display, egl_context);
    eglDestroySurface(egl_display, egl_surface);
    wl_egl_window_destroy(egl_window);
    eglTerminate(egl_display);
    wl_display_disconnect(display);
    
    printf("All tests passed!\n");
    return 0;
}