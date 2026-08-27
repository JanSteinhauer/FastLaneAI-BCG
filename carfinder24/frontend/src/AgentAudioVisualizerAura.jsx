/**
 * Aura shader adapted from LiveKit Agents UI's AgentAudioVisualizerAura.
 *
 * Originally developed for Unicorn Studio (https://unicorn.studio) and
 * licensed under the Polyform Non-Resale License 1.0.0.
 * https://polyformproject.org/licenses/non-resale/1.0.0/
 *
 * The small WebGL renderer below is purpose-built for this shader so this
 * event demo does not need React 19, Tailwind, Motion, or shadcn/ui.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useTrackVolume } from "@livekit/components-react";

const DEFAULT_COLOR = "#1FD5F9";

const VERTEX_SHADER = `
attribute vec2 aPosition;

void main() {
  gl_Position = vec4(aPosition, 0.0, 1.0);
}`;

const AURA_SHADER = `
const float TAU = 6.283185;

vec2 randFibo(vec2 p) {
  p = fract(p * vec2(443.897, 441.423));
  p += dot(p, p.yx + 19.19);
  return fract((p.xx + p.yx) * p.xy);
}

vec3 Tonemap(vec3 x) {
  x *= 4.0;
  return x / (1.0 + x);
}

float luma(vec3 color) {
  return dot(color, vec3(0.299, 0.587, 0.114));
}

vec3 rgb2hsv(vec3 c) {
  vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
  vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
  vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10;
  return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

vec3 hsv2rgb(vec3 c) {
  vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
  vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

float sdCircle(vec2 st, float r) {
  return length(st) - r;
}

float sdLine(vec2 p, float r) {
  float halfLen = r * 2.0;
  vec2 a = vec2(-halfLen, 0.0);
  vec2 b = vec2(halfLen, 0.0);
  vec2 pa = p - a;
  vec2 ba = b - a;
  float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
  return length(pa - ba * h);
}

float getSdf(vec2 st) {
  if (uShape == 1.0) return sdCircle(st, uScale);
  if (uShape == 2.0) return sdLine(st, uScale);
  return sdCircle(st, uScale);
}

vec2 turb(vec2 pos, float t, float it) {
  mat2 rotation = mat2(0.6, -0.25, 0.25, 0.9);
  mat2 layerRotation = mat2(0.6, -0.8, 0.8, 0.6);
  float frequency = mix(2.0, 15.0, uFrequency);
  float amplitude = uAmplitude;
  float animTime = t * 0.1 * uSpeed;

  for (int i = 0; i < 4; i++) {
    vec2 rotatedPos = pos * rotation;
    vec2 wave = sin(frequency * rotatedPos + float(i) * animTime + it);
    pos += (amplitude / frequency) * rotation[0] * wave;
    rotation *= layerRotation;
    amplitude *= mix(1.0, max(wave.x, wave.y), uVariance);
    frequency *= 1.4;
  }

  return pos;
}

const float ITERATIONS = 28.0;

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
  vec2 uv = fragCoord / iResolution.xy;
  vec3 pp = vec3(0.0);
  vec3 bloom = vec3(0.0);
  float t = iTime * 0.5;
  vec2 pos = uv - 0.5;
  vec2 prevPos = turb(pos, t, -1.0 / ITERATIONS);
  float spacing = mix(1.0, TAU, uSpacing);

  for (float i = 1.0; i < ITERATIONS + 1.0; i++) {
    float iter = i / ITERATIONS;
    vec2 st = turb(pos, t, iter * spacing);
    float d = abs(getSdf(st));
    float pd = distance(st, prevPos);
    prevPos = st;
    float dynamicBlur = exp2(pd * 2.0 * 1.4426950408889634) - 1.0;
    float ds = smoothstep(0.0, uBlur * 0.05 + max(dynamicBlur * uSmoothing, 0.001), d);
    vec3 layerColor = uColor;

    if (uColorShift > 0.01) {
      vec3 hsv = rgb2hsv(layerColor);
      hsv.x = fract(hsv.x + (1.0 - iter) * uColorShift * 0.3);
      layerColor = hsv2rgb(hsv);
    }

    float invd = 1.0 / max(d + dynamicBlur, 0.001);
    pp += (ds - 1.0) * layerColor;
    bloom += clamp(invd, 0.0, 250.0) * layerColor;
  }

  pp *= 1.0 / ITERATIONS;
  vec3 color;

  if (uMode < 0.5) {
    bloom = bloom / (bloom + 2e4);
    color = (-pp + bloom * 3.0 * uBloom) * 1.2;
    color += (randFibo(fragCoord).x - 0.5) / 255.0;
    color = Tonemap(color);
    float alpha = luma(color) * uMix;
    fragColor = vec4(color * uMix, alpha);
  } else {
    color = -pp;
    color += (randFibo(fragCoord).x - 0.5) / 255.0;
    float brightness = length(color);
    vec3 direction = brightness > 0.0 ? color / brightness : color;
    float mappedBrightness = (brightness * 2.0) / (1.0 + brightness * 2.0);
    color = direction * mappedBrightness;
    float gray = dot(color, vec3(0.2, 0.5, 0.1));
    color = clamp(mix(vec3(gray), color, 3.0), 0.0, 1.0);
    float alpha = mappedBrightness * clamp(uMix, 1.0, 2.0);
    fragColor = vec4(color, alpha);
  }
}

void main() {
  vec4 color = vec4(0.0);
  mainImage(color, gl_FragCoord.xy);
  gl_FragColor = color;
}`;

const FRAGMENT_SHADER = `
precision highp float;
uniform float iTime;
uniform vec2 iResolution;
uniform float uSpeed;
uniform float uBlur;
uniform float uScale;
uniform float uShape;
uniform float uFrequency;
uniform float uAmplitude;
uniform float uBloom;
uniform float uMix;
uniform float uSpacing;
uniform float uColorShift;
uniform float uVariance;
uniform float uSmoothing;
uniform float uMode;
uniform vec3 uColor;
${AURA_SHADER}`;

const STATE_PARAMETERS = {
  idle: { speed: 4, scale: 0.28, amplitude: 0.6, frequency: 0.45, brightness: 1.35 },
  failed: { speed: 4, scale: 0.28, amplitude: 0.6, frequency: 0.45, brightness: 1.35 },
  disconnected: {
    speed: 4,
    scale: 0.28,
    amplitude: 0.6,
    frequency: 0.45,
    brightness: 1.35,
  },
  listening: {
    speed: 6,
    scale: 0.3,
    amplitude: 0.6,
    frequency: 0.45,
    brightness: 1.5,
  },
  "pre-connect-buffering": {
    speed: 6,
    scale: 0.3,
    amplitude: 0.6,
    frequency: 0.45,
    brightness: 1.5,
  },
  thinking: { speed: 7, scale: 0.3, amplitude: 0.58, frequency: 0.48, brightness: 1.45 },
  connecting: { speed: 7, scale: 0.3, amplitude: 0.58, frequency: 0.48, brightness: 1.45 },
  initializing: { speed: 7, scale: 0.3, amplitude: 0.58, frequency: 0.48, brightness: 1.45 },
  speaking: { speed: 6, scale: 0.3, amplitude: 0.6, frequency: 0.45, brightness: 1.5 },
};

const SIZE_CLASS = {
  icon: "aura--icon",
  sm: "aura--sm",
  md: "aura--md",
  lg: "aura--lg",
  xl: "aura--xl",
};

const SIZE_VALUE = {
  icon: "24px",
  sm: "56px",
  md: "112px",
  lg: "224px",
  xl: "min(448px, 70vw)",
};

function hexToRgb(hexColor) {
  const match = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hexColor);
  if (!match) return hexToRgb(DEFAULT_COLOR);
  return match.slice(1).map((channel) => parseInt(channel, 16) / 255);
}

function compileShader(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);

  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const message = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(message || "Could not compile the Aura shader");
  }

  return shader;
}

function createProgram(gl) {
  const program = gl.createProgram();
  const vertex = compileShader(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
  const fragment = compileShader(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  gl.deleteShader(vertex);
  gl.deleteShader(fragment);

  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const message = gl.getProgramInfoLog(program);
    gl.deleteProgram(program);
    throw new Error(message || "Could not link the Aura shader");
  }

  return program;
}

function AuraCanvas({ parameters, color, colorShift, themeMode }) {
  const canvasRef = useRef(null);
  const parametersRef = useRef(parameters);
  const appearanceRef = useRef({ color: hexToRgb(color), colorShift, themeMode });
  const [shaderFailed, setShaderFailed] = useState(false);

  parametersRef.current = parameters;
  appearanceRef.current = { color: hexToRgb(color), colorShift, themeMode };

  useEffect(() => {
    const canvas = canvasRef.current;
    const gl = canvas?.getContext("webgl", {
      alpha: true,
      antialias: false,
      premultipliedAlpha: false,
    });

    if (!canvas || !gl) {
      setShaderFailed(true);
      return undefined;
    }

    let program;
    try {
      program = createProgram(gl);
    } catch (error) {
      console.error("Aura shader error:", error);
      setShaderFailed(true);
      return undefined;
    }

    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
      gl.STATIC_DRAW,
    );

    gl.useProgram(program);
    const position = gl.getAttribLocation(program, "aPosition");
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

    const location = (name) => gl.getUniformLocation(program, name);
    const locations = {
      time: location("iTime"),
      resolution: location("iResolution"),
      speed: location("uSpeed"),
      blur: location("uBlur"),
      scale: location("uScale"),
      shape: location("uShape"),
      frequency: location("uFrequency"),
      amplitude: location("uAmplitude"),
      bloom: location("uBloom"),
      mix: location("uMix"),
      spacing: location("uSpacing"),
      colorShift: location("uColorShift"),
      variance: location("uVariance"),
      smoothing: location("uSmoothing"),
      mode: location("uMode"),
      color: location("uColor"),
    };

    let animationFrame;
    let visible = true;
    let lastFrameAt = performance.now();
    let shaderTime = 0;
    let pulsePhase = 0;
    const initialParameters = parametersRef.current;
    const current = { ...initialParameters };
    let voiceEnvelope = initialParameters.voiceEnergy ?? 0;
    delete current.voiceEnergy;
    // Crossfaded separately from `current`: the color changes per persona,
    // not per state, and lives in appearanceRef.
    const currentColor = [...appearanceRef.current.color];

    const resize = () => {
      const ratio = Math.min(globalThis.devicePixelRatio || 1, 1);
      const width = Math.max(1, Math.round(canvas.clientWidth * ratio));
      const height = Math.max(1, Math.round(canvas.clientHeight * ratio));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
    };

    const render = (now) => {
      if (!visible) return;
      resize();
      const frameSeconds = Math.min(0.1, Math.max(0, (now - lastFrameAt) / 1000));
      lastFrameAt = now;
      const target = parametersRef.current;
      const stateMix = 1 - Math.exp(-frameSeconds / 0.65);

      for (const key of Object.keys(current)) {
        current[key] += (target[key] - current[key]) * stateMix;
      }

      const targetVoiceEnergy = target.voiceEnergy ?? 0;
      const envelopeTime = targetVoiceEnergy > voiceEnvelope ? 0.12 : 0.3;
      const envelopeMix = 1 - Math.exp(-frameSeconds / envelopeTime);
      voiceEnvelope += (targetVoiceEnergy - voiceEnvelope) * envelopeMix;
      const naturalVoiceEnergy =
        voiceEnvelope * voiceEnvelope * (3 - 2 * voiceEnvelope);
      shaderTime += frameSeconds * current.speed;
      pulsePhase += frameSeconds * current.pulseSpeed;

      const appearance = appearanceRef.current;
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform1f(locations.time, shaderTime);
      gl.uniform2f(locations.resolution, canvas.width, canvas.height);
      // Speed is integrated into shaderTime so changing states never jumps the
      // shader backwards or forwards in its animation phase.
      gl.uniform1f(locations.speed, 1);
      gl.uniform1f(locations.blur, 0.2);
      gl.uniform1f(locations.scale, current.scale + 0.04 * naturalVoiceEnergy);
      gl.uniform1f(locations.shape, 1);
      gl.uniform1f(locations.frequency, current.frequency);
      gl.uniform1f(locations.amplitude, current.amplitude);
      gl.uniform1f(locations.bloom, 0);
      const pulsedBrightness =
        current.brightness +
        0.12 * naturalVoiceEnergy +
        Math.sin(pulsePhase) * current.pulseAmplitude;
      gl.uniform1f(locations.mix, pulsedBrightness);
      gl.uniform1f(locations.spacing, 0.5);
      gl.uniform1f(locations.colorShift, appearance.colorShift);
      gl.uniform1f(locations.variance, 0.1);
      gl.uniform1f(locations.smoothing, 1);
      gl.uniform1f(locations.mode, appearance.themeMode === "light" ? 1 : 0);
      for (let i = 0; i < 3; i += 1) {
        currentColor[i] += (appearance.color[i] - currentColor[i]) * stateMix;
      }
      gl.uniform3fv(locations.color, currentColor);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      animationFrame = requestAnimationFrame(render);
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);
    const intersectionObserver = new IntersectionObserver(([entry]) => {
      const wasVisible = visible;
      visible = entry?.isIntersecting ?? true;
      if (visible && !wasVisible) animationFrame = requestAnimationFrame(render);
    });
    intersectionObserver.observe(canvas);
    animationFrame = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
      intersectionObserver.disconnect();
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
    };
  }, []);

  if (shaderFailed) return <div className="aura-fallback" aria-hidden="true" />;
  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{ display: "block", width: "100%", height: "100%" }}
    />
  );
}

export function AgentAudioVisualizerAura({
  size = "lg",
  state = "connecting",
  color = DEFAULT_COLOR,
  colorShift = 0.05,
  themeMode = "dark",
  audioTrack,
  volume,
  className = "",
  style,
  ...props
}) {
  const measuredAgentVolume = useTrackVolume(audioTrack, {
    fftSize: 512,
    smoothingTimeConstant: 0.55,
  });
  const agentVolume = volume ?? measuredAgentVolume;
  const normalizeVolume = (value) =>
    Math.min(1, Math.max(0, (value - 0.05) / 0.65));
  const voiceEnergy = normalizeVolume(agentVolume);
  const base = STATE_PARAMETERS[state] ?? STATE_PARAMETERS.connecting;
  const parameters = useMemo(() => {
    const isListening =
      state === "listening" || state === "pre-connect-buffering";
    const isThinking = ["thinking", "connecting", "initializing"].includes(
      state,
    );

    return {
      ...base,
      voiceEnergy,
      pulseAmplitude: isListening ? 0.04 : isThinking ? 0.08 : 0,
      pulseSpeed: isListening ? 1.8 : 1.5,
    };
  }, [base, state, voiceEnergy]);

  return (
    <div
      className={`agent-audio-visualizer-aura ${SIZE_CLASS[size] ?? SIZE_CLASS.lg} ${className}`.trim()}
      data-lk-state={state}
      role="img"
      aria-label={`Voice agent is ${state}`}
      style={{
        width: SIZE_VALUE[size] ?? SIZE_VALUE.lg,
        height: SIZE_VALUE[size] ?? SIZE_VALUE.lg,
        ...style,
      }}
      {...props}
    >
      <AuraCanvas
        parameters={parameters}
        color={color}
        colorShift={colorShift}
        themeMode={themeMode}
      />
    </div>
  );
}
