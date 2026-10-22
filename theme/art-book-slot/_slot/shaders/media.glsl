// Art Book Slot, MIT. Crop-preserving video inside physical media surfaces.
#if defined(VERTEX)
uniform mat4 MVPMatrix;
attribute vec2 VertexCoord;
attribute vec2 TexCoord;
attribute vec4 COLOR;
varying vec2 mediaPosition;
varying vec2 videoUV;
varying vec4 tint;
void main() {
    gl_Position = MVPMatrix * vec4(VertexCoord, 0.0, 1.0);
    mediaPosition = VertexCoord;
    videoUV = TexCoord;
    tint = COLOR;
}
#elif defined(FRAGMENT)
#ifdef GL_ES
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
#endif
uniform sampler2D u_tex;
uniform vec2 outputSize;
uniform vec2 outputOffset;
uniform vec2 textureSize;
uniform float saturation;
uniform float mediaMode;
uniform float mediaOuter;
uniform float mediaInner;
uniform vec2 mediaSize;
uniform vec4 mediaWell0;
uniform vec4 mediaWell1;
uniform vec4 mediaWell2;
uniform float mediaCorner0;
uniform float mediaCorner1;
uniform float mediaCorner2;
uniform vec4 mediaCanvas;
// Optional part of the video to crop within (x, y, w, h in video UV); unset
// means the whole frame. DS clips stack two screens in a portrait frame; the
// label shows the top one.
uniform vec4 mediaSource;
uniform vec4 mediaMap0;
uniform vec4 mediaMap1;
uniform vec4 mediaMap2;
varying vec2 mediaPosition;
varying vec2 videoUV;
varying vec4 tint;

void main() {
    vec2 dimensions = max(abs(outputSize), vec2(1.0));
    vec2 local = (mediaPosition - outputOffset) / dimensions;
    vec2 uv = videoUV;
    float coverage;
    float hubEdge = 0.0;
    if (mediaMode > 0.5) {
        // Map the projected poster back to the actual flat CD/UMD plane.
        vec3 point = vec3(local, 1.0);
        float denominator = dot(mediaMap2.xyz, point);
        vec2 plane = vec2(dot(mediaMap0.xyz, point), dot(mediaMap1.xyz, point)) / denominator;
        float radius = length(plane - vec2(0.5));
        float px = 1.0 / min(dimensions.x, dimensions.y);
        float aa = 0.75 * px;
        coverage = 1.0 - smoothstep(mediaOuter-aa, mediaOuter+aa, radius);
        if (mediaInner > 0.0) {
            // Draw the moulded hub edge concentric with the hole, so printed
            // poster art never shows through the antialiased transition.
            float hub = mediaInner - 2.5*px;
            coverage *= smoothstep(hub-aa, hub+aa, radius);
            hubEdge = 1.0 - smoothstep(mediaInner-aa, mediaInner+aa, radius);
        }
        // One uniform scale to a square canvas, then crop. Never squeeze axes.
        vec2 source = max(textureSize, vec2(1.0));
        vec2 retained = min(vec2(1.0), source.yx / source.xy);
        vec2 canvas = (plane-mediaCanvas.xy) / mediaCanvas.zw;
        uv = vec2(0.5) + (canvas-vec2(0.5)) * retained;
    } else {
        float surface = floor((1.0-saturation)*4.0+0.5);
        vec4 well = surface>1.5 ? mediaWell2 : surface>0.5 ? mediaWell1 : mediaWell0;
        float radius = surface>1.5 ? mediaCorner2 : surface>0.5 ? mediaCorner1 : mediaCorner0;
        vec2 canvas = (local-well.xy) / well.zw;
        vec2 label = dimensions * well.zw;
        vec2 halfSize = label * 0.5;
        float corner = min(radius*dimensions.x/mediaSize.x, min(halfSize.x,halfSize.y));
        vec2 q = abs(canvas*label-halfSize) - halfSize + corner;
        float distance = length(max(q, vec2(0.0))) + min(max(q.x,q.y),0.0) - corner;
        coverage = 1.0 - smoothstep(-0.75, 0.75, distance);
        // Only a portrait frame holds stacked screens; others use the whole frame.
        bool stacked = mediaSource.z > 0.0 && textureSize.y > textureSize.x;
        vec4 region = stacked ? mediaSource : vec4(0.0, 0.0, 1.0, 1.0);
        vec2 source = max(textureSize,vec2(1.0)) * region.zw;
        float aspect = (label.x/label.y) / (source.x/source.y);
        vec2 retained = min(vec2(1.0),vec2(aspect,1.0/aspect));
        uv = region.xy + (vec2(0.5)+(canvas-vec2(0.5))*retained) * region.zw;
    }
    vec4 pixel = texture2D(u_tex, uv);
    pixel.rgb = mix(pixel.rgb, vec3(0.38, 0.41, 0.42), hubEdge);
    pixel.a *= tint.a;
    pixel.a *= coverage;
    gl_FragColor = pixel;
}
#endif
