// Source for the pre-built bundle in frontend/dist/app.{js,css}.
// Rebuild with `npm install && npm run build` in frontend/ — see README.md.

import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  DisconnectButton,
  LiveKitRoom,
  RoomAudioRenderer,
  StartAudio,
  TrackToggle,
  useRoomContext,
  useTracks,
  useVoiceAssistant,
  VideoTrack,
} from "@livekit/components-react";
import { Track } from "livekit-client";
import "@livekit/components-styles";
import { AgentAudioVisualizerAura } from "./AgentAudioVisualizerAura";

function BrandHeader({ live = false }) {
  return (
    <header className="brand-header">
      <span className="brand-logo" role="img" aria-label="BCG X" />
      <span className="demo-badge">
        <span className={live ? "demo-dot demo-dot--live" : "demo-dot"} />
        {live ? "Live session" : "Recruiting demo"}
      </span>
    </header>
  );
}

// A short two-note chime for the moment the offer lands. Synthesised rather
// than shipped as an audio file: no asset to load, nothing to go missing, and
// it stays quiet enough not to fight the advisor's voice.
let audioCtx = null;

function playSentChime() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    audioCtx = audioCtx || new Ctx();
    if (audioCtx.state === "suspended") audioCtx.resume();
    const now = audioCtx.currentTime;
    // A5 then E6 — a rising interval reads as "done", not as an alert.
    [[880, 0], [1318.51, 0.085]].forEach(([freq, offset]) => {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.0001, now + offset);
      gain.gain.exponentialRampToValueAtTime(0.11, now + offset + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + offset + 0.4);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start(now + offset);
      osc.stop(now + offset + 0.42);
    });
  } catch (e) {
    // Audio is a nicety; never let it break the call.
  }
}

function Toast({ payload, onClose }) {
  useEffect(() => {
    if (!payload) return undefined;
    const timer = setTimeout(onClose, 5200);
    return () => clearTimeout(timer);
  }, [payload, onClose]);

  if (!payload) return null;
  const detail = [payload.recipient, payload.reference].filter(Boolean).join(" \u00b7 ");

  return (
    <div className="toast" role="status" aria-live="polite">
      <svg className="toast-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="2.75" y="4.75" width="18.5" height="14.5" rx="2.25" stroke="currentColor" strokeWidth="1.7" />
        <path d="m3.5 7 7.35 5.4a2 2 0 0 0 2.3 0L20.5 7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      </svg>
      <div className="toast-body">
        <span className="toast-title">Offer sent</span>
        {detail && <span className="toast-sub">{detail}</span>}
      </div>
    </div>
  );
}

// Renders whatever an agent tool pushed via used_car_advisor.ui.push (topic "ui").
// Payload shapes: cars | quote | sent | text — see src/used_car_advisor/ui.py.
function CarCard({ car }) {
  return (
    <div className="car-card">
      {car.image && <img src={car.image} alt="" />}
      <div className="body">
        <span className="title">{car.title}</span>
        {car.price && <span className="price">{car.price}</span>}
        {car.sub && <span className="sub">{car.sub}</span>}
        <span className="meta">
          {[
            car.year,
            car.mileage_km != null
              ? `${car.mileage_km.toLocaleString("de-DE")} km`
              : null,
            car.fuel,
          ]
            .filter(Boolean)
            .join(" \u00b7 ")}
        </span>
        {car.meta2 && <span className="meta">{car.meta2}</span>}
      </div>
    </div>
  );
}

function QuoteCard({ payload }) {
  return (
    <div className="quote-card">
      <div className="quote-head">
        <span className="quote-title">{payload.title}</span>
        <span className="quote-headline">{payload.headline}</span>
        <span className="quote-note">{payload.headline_note}</span>
      </div>
      <table className="quote-rows">
        <tbody>
          {(payload.rows || []).map(([label, value], i) => (
            <tr key={i}>
              <td>{label}</td>
              <td>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {payload.footnote && <div className="quote-foot">{payload.footnote}</div>}
    </div>
  );
}

function SentCard({ payload }) {
  return (
    <div className="sent-card">
      <span className="sent-check" aria-hidden="true" />
      <div>
        <div className="sent-title">
          {payload.title} <span className="sent-to">{payload.recipient}</span>
        </div>
        <div className="sent-note">{payload.note}</div>
        {payload.reference && (
          <div className="sent-ref">Reference {payload.reference}</div>
        )}
      </div>
    </div>
  );
}

function ToolPanel({ payload }) {
  if (!payload) return null;
  if (payload.type === "cars" && Array.isArray(payload.cars)) {
    return (
      <div className="panel">
        {payload.subtitle && <div className="panel-title">{payload.subtitle}</div>}
        <div className="cars">
          {payload.cars.map((car, i) => (
            <CarCard car={car} key={car.ref || i} />
          ))}
        </div>
      </div>
    );
  }
  if (payload.type === "quote") {
    return (
      <div className="panel">
        <QuoteCard payload={payload} />
      </div>
    );
  }
  if (payload.type === "sent") {
    return (
      <div className="panel">
        <SentCard payload={payload} />
      </div>
    );
  }
  if (payload.type === "text" && payload.text) {
    return (
      <div className="panel">
        <div className="bubble">{payload.text}</div>
      </div>
    );
  }
  // Unknown payload shape — show it raw so custom tools still get feedback.
  return (
    <div className="panel">
      <div className="bubble">{JSON.stringify(payload, null, 2)}</div>
    </div>
  );
}

// Aura color before the agent joins / when the backend doesn't send one.
const DEFAULT_AURA_COLOR = "#00E0B5";

// useVoiceAssistant states meaning "the agent isn't ready to talk yet". In
// avatar chats the worker holds the session in these states until the avatar's
// video is published, so the same check covers the Tavus join wait.
const LOADING_STATES = new Set(["disconnected", "connecting", "initializing"]);

function Chat() {
  const { state, audioTrack: agentAudioTrack, agentAttributes } =
    useVoiceAssistant();
  const room = useRoomContext();
  const [payload, setPayload] = useState(null);
  const [toast, setToast] = useState(null);
  const persona = agentAttributes?.agent;
  const auraColor = agentAttributes?.agent_color || DEFAULT_AURA_COLOR;

  // Avatar chat (web client started with --avatar): each Tavus participant
  // publishes lip-synced video for one persona (identity "tavus-avatar-<name>").
  // ALL feeds stay mounted (mounting VideoTrack subscribes the stream) with
  // only the active persona's visible, so a handoff flips faces instantly.
  const cameraTracks = useTracks([Track.Source.Camera], {
    onlySubscribed: false,
  });
  const avatarTracks = cameraTracks.filter((t) =>
    t.participant.identity.startsWith("tavus-avatar-"),
  );
  const personaKey = persona ? persona.replace(/Agent$/, "").toLowerCase() : "";
  const activeAvatar =
    avatarTracks.find(
      (t) => t.participant.identity === `tavus-avatar-${personaKey}`,
    ) ?? avatarTracks[0];

  let stage;
  if (avatarTracks.length > 0) {
    stage = avatarTracks.map((t) => (
      <VideoTrack
        key={t.participant.identity}
        trackRef={t}
        className={
          t === activeAvatar
            ? "avatar-video"
            : "avatar-video avatar-video--hidden"
        }
        style={{ "--persona-color": auraColor }}
      />
    ));
  } else if (LOADING_STATES.has(state)) {
    stage = (
      <output className="stage-loader" aria-label="Connecting">
        <span className="stage-loader-ring" />
      </output>
    );
  } else {
    stage = (
      <AgentAudioVisualizerAura
        size="lg"
        state={state}
        color={auraColor}
        colorShift={0.4}
        themeMode="dark"
        audioTrack={agentAudioTrack}
        data-lk-persona={persona || "unassigned"}
        data-lk-aura-color={auraColor}
      />
    );
  }

  useEffect(() => {
    room.registerTextStreamHandler("ui", async (reader) => {
      const text = await reader.readAll();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        data = { type: "text", text };
      }
      setPayload(data);
      // The email is the end of the journey — announce it, don't just draw it.
      if (data.type === "sent") {
        setToast(data);
        playSentChime();
      }
    });
    return () => room.unregisterTextStreamHandler("ui");
  }, [room]);

  return (
    <>
      <div className="aura-stage">{stage}</div>
      <p className="status">
        {state}
        {persona && <> — {persona}</>}
      </p>
      <ToolPanel payload={payload} />
      <Toast payload={toast} onClose={() => setToast(null)} />
      <div className="controls">
        <TrackToggle source={Track.Source.Microphone}>Mic</TrackToggle>
        <DisconnectButton>End chat</DisconnectButton>
      </div>
      <StartAudio label="Click to allow audio" />
    </>
  );
}

function App() {
  const [conn, setConn] = useState(null);
  const [error, setError] = useState(null);

  // Fetching + connecting from the click handler keeps browser autoplay rules happy.
  const start = async () => {
    setError(null);
    try {
      const res = await fetch("/token");
      if (!res.ok) throw new Error(await res.text());
      setConn(await res.json());
    } catch (e) {
      setError(String(e));
    }
  };

  if (!conn) {
    return (
      <div className="widget widget--intro">
        <BrandHeader />
        <main className="hero">
          <p className="eyebrow">Your voice-powered used-car advisor</p>
          <h1>CarFinder24</h1>
          <p className="tagline">
            Tell us what matters. We’ll turn the conversation into a focused
            shortlist of cars that fit.
          </p>
          <button className="start" onClick={start}>
            <span className="start-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path d="M12 15.5a3.5 3.5 0 0 0 3.5-3.5V6a3.5 3.5 0 1 0-7 0v6a3.5 3.5 0 0 0 3.5 3.5Z" />
                <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3M9 21h6" />
              </svg>
            </span>
            Start conversation
            <span className="start-arrow" aria-hidden="true">→</span>
          </button>
        </main>
        {error && (
          <p className="error">
            Could not start the chat: {error}. Is your .env filled in?
          </p>
        )}
        <p className="hint">
          <span>Local demo</span>
          <code>uv run used-car-advisor dev</code>
        </p>
      </div>
    );
  }

  return (
    <div className="widget widget--session" data-lk-theme="default">
      <BrandHeader live />
      <div className="session-intro">
        <p className="eyebrow">Your voice-powered used-car advisor</p>
        <h1>CarFinder24</h1>
        <p className="tagline">Unmute the mic below and speak naturally.</p>
      </div>
      <LiveKitRoom
        serverUrl={conn.serverUrl}
        token={conn.token}
        connect
        // Join muted: no mic is published (or permission asked) until the
        // visitor enables it via the Mic toggle below.
        audio={false}
        video={false}
        onDisconnected={() => setConn(null)}
        onError={(e) => {
          setError(String(e));
          setConn(null);
        }}
        style={{ display: "contents" }}
      >
        <Chat />
        <RoomAudioRenderer />
      </LiveKitRoom>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
