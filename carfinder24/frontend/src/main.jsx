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

// One inline SVG silhouette per body_type family, shared by the OfferCard's
// stage and the CarTypeFilterPanel's icons. Body color comes in through the
// --car-color custom property (see page.css) rather than a fill prop, so the
// filter panel can animate it on selection instead of just swapping it.
const CAR_SHAPES = {
  sedan: {
    body: "M30,76 C26,76 24,70 26,64 L34,58 Q46,52 60,50 Q72,30 92,28 L124,28 Q142,30 148,44 Q152,50 160,52 Q170,54 172,64 L172,76 Z",
    rim: "M35,58 Q60,32 92,29",
  },
  wagon: {
    body: "M30,76 C26,76 24,70 26,64 L34,58 Q46,52 60,50 Q72,30 92,28 L136,28 Q150,29 156,36 L160,50 Q162,58 164,64 L172,68 L172,76 Z",
    rim: "M35,58 Q60,32 92,29 L134,29",
  },
  suv: {
    body: "M28,76 L28,60 Q28,52 36,50 L40,44 Q46,26 64,24 L132,24 Q150,26 156,44 L162,52 Q168,54 172,60 L172,76 Z",
    rim: "M40,49 Q46,27 64,25 L132,25",
  },
  van: {
    body: "M26,76 L26,30 Q26,22 34,22 L164,22 Q172,22 172,30 L172,76 Z",
    rim: "M27,29 Q27,23 34,23 L164,23",
  },
  coupe: {
    body: "M30,76 C27,76 25,70 27,62 L36,54 Q54,50 66,48 Q84,32 108,30 Q132,30 148,40 Q162,50 168,60 Q172,64 172,76 Z",
    rim: "M38,53 Q66,34 108,31",
  },
  convertible: {
    body: "M30,76 C27,76 25,70 27,62 L36,54 Q54,50 64,48 L100,40 Q120,40 138,44 Q158,50 168,60 Q172,64 172,76 Z",
    rim: "M42,49 L100,41 Q120,41 138,45",
  },
  compact: {
    body: "M34,76 C30,76 28,70 30,64 Q32,54 42,50 Q52,34 70,32 L108,32 Q126,34 134,46 Q140,54 148,58 Q160,62 166,68 Q168,72 168,76 Z",
    rim: "M40,49 Q52,36 70,33 L106,33",
  },
};

const BODY_TYPE_ORDER = ["sedan", "wagon", "suv", "van", "coupe", "convertible", "compact"];

const BODY_TYPE_LABEL = {
  sedan: "Sedan", wagon: "Estate", suv: "SUV", van: "Van",
  coupe: "Coupe", convertible: "Convertible", compact: "Compact",
};

// The dataset's raw body_type strings (cars_mcp/server.py's BODY_TYPES lists
// the reverse of this — customer word -> raw value; this is raw value -> icon).
const BODY_TYPE_TO_SHAPE = {
  "sedan": "sedan",
  "station wagon": "wagon", "station wagon/van": "wagon",
  "off-road/pick-up": "suv",
  "van": "van", "van-high roof": "van", "transporter": "van", "panel van": "van",
  "flatbed van": "van", "flatbed+tarpaulin": "van", "box": "van",
  "breakdown truck": "van", "car transport": "van", "hydraulic work platform": "van",
  "coupe": "coupe",
  "convertible": "convertible",
  "compact": "compact", "other": "compact",
};

// body_color as the dataset spells it -> a real paint hex. Unmapped/missing
// colors fall back to the dashed "no color on file" outline (see .no-color).
const COLOR_HEX = {
  blue: "#3568b0", grey: "#8a8d93", green: "#3e7c4a", white: "#e9e9ea",
  red: "#b23a2e", black: "#232326", violet: "#6c4ab6", orange: "#d97a28",
  yellow: "#d9b23c", bronze: "#8c6b3f", brown: "#6b4226", beige: "#d8c3a0",
  gold: "#b8912f", silver: "#b7bac0",
};

function CarGlyph({ shape, carColor, active = false, className = "" }) {
  const def = CAR_SHAPES[shape] || CAR_SHAPES.compact;
  return (
    <svg
      viewBox="0 0 200 100"
      className={`car-glyph ${active ? "is-active" : ""} ${carColor ? "" : "no-color"} ${className}`.trim()}
      style={carColor ? { "--car-color": carColor } : undefined}
      aria-hidden="true"
    >
      <ellipse className="glyph-ground" cx="100" cy="88" rx="70" ry="8" />
      <circle className="glyph-wheel" cx="55" cy="80" r="13" />
      <circle className="glyph-hub" cx="55" cy="80" r="5" />
      <circle className="glyph-wheel" cx="145" cy="80" r="13" />
      <circle className="glyph-hub" cx="145" cy="80" r="5" />
      <path className="glyph-body" d={def.body} />
      <path className="glyph-rim" d={def.rim} />
    </svg>
  );
}

// The live filter-state display: every one of the 7 body-type icons is always
// rendered (so the customer can see the full vocabulary the advisor
// understands), and the one matching `active.body_type_icon` recolors — see
// used_car_advisor.ui.filters_payload for how that field is derived from
// find_cars' arguments, and .car-glyph's --car-color transition in page.css
// for the animation itself.
function CarTypeFilterPanel({ active }) {
  const activeKey = active?.body_type_icon || null;
  return (
    <div className="filter-panel" role="group" aria-label="Vehicle type the advisor is searching for">
      {BODY_TYPE_ORDER.map((key) => {
        const isActive = key === activeKey;
        return (
          <div key={key} className={`filter-chip-icon ${isActive ? "is-active" : ""}`}>
            <CarGlyph shape={key} active={isActive} carColor={isActive ? "var(--accent)" : null} />
            <span className="filter-chip-label">{BODY_TYPE_LABEL[key]}</span>
          </div>
        );
      })}
    </div>
  );
}

function fmtEur(value, decimals = 0) {
  if (value === null || value === undefined) return "—";
  return `€${value.toLocaleString("de-DE", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

// The min/med/max market-position bar inside OfferCard's price panel — only
// rendered when price_check found comparables (payload.comparison is null
// otherwise, e.g. a rare make/model with too few matches to judge).
// The make's logo from public/CarLogo/, named after the slugified make so the
// path needs no lookup table. Nine makes have no file (Audi is the big one), and
// a logo could 404 for any reason, so it degrades to the typographic monogram
// rather than leaving a hole. Logos sit on a light chip: more than half of them
// are black-on-transparent silhouettes and would be invisible on a dark card.
function BrandMark({ make }) {
  const [failed, setFailed] = useState(false);
  const slug = (make || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const monogram = (make || "?").slice(0, 2).toUpperCase();

  if (!slug || failed) return <span className="make-mark">{monogram}</span>;
  return (
    <span className="make-logo">
      <img
        src={`/public/CarLogo/${slug}.svg`}
        alt=""
        loading="lazy"
        onError={() => setFailed(true)}
      />
    </span>
  );
}

function PriceBar({ priceEur, comparison }) {
  const [min, max] = comparison.range_eur || [];
  if (min == null || max == null || max === min) return null;
  const clamp = (v) => Math.min(100, Math.max(0, v));
  const pricePos = clamp(((priceEur - min) / (max - min)) * 100);
  const medianPos = clamp(((comparison.median_price_eur - min) / (max - min)) * 100);
  return (
    <div className="price-bar">
      <div
        className={`bar-fill bar-fill--${comparison.direction}`}
        style={{
          clipPath:
            comparison.direction === "above"
              ? `inset(0 0 0 ${medianPos}%)`
              : `inset(0 ${100 - pricePos}% 0 0)`,
        }}
      />
      <div className="bar-tick" style={{ left: `${medianPos}%` }}>
        <span className="bar-tick-label">med {fmtEur(comparison.median_price_eur)}</span>
      </div>
      <div className={`bar-marker bar-marker--${comparison.direction}`} style={{ left: `${pricePos}%` }} />
      <div className="bar-endlabels">
        <span>{fmtEur(min)}</span>
        <span>{fmtEur(max)}</span>
      </div>
    </div>
  );
}

// The fused car_details + price_check + leasing_quote view — see
// used_car_advisor.ui.offer_payload and tools.show_offer. Starts collapsed to
// the price and market verdict; "Leasing details" is a native <details>, so
// the breakdown needs no component state of its own.
function OfferCard({ payload }) {
  const {
    make, title, body_type, body_color, year, mileage_km, power_hp, fuel, transmission,
    drive_train, seller, city, ratings_average, ratings_count, had_accident,
    full_service_history, previous_owners, consumption_l_100km, co2_g_km,
    price_eur, monthly_rate_eur, leasing_factor_pct, term_months, annual_km,
    down_payment_eur, breakdown = {}, total_cost_eur, cost_per_km_eur, comparison, footnote,
  } = payload;

  const shapeKey = BODY_TYPE_TO_SHAPE[(body_type || "").toLowerCase()] || "compact";
  const carColor = COLOR_HEX[(body_color || "").toLowerCase()] || null;
  return (
    <div className="offer-card">
      <div className="offer-head">
        <BrandMark make={make} />
        <span className="make-name">{make}</span>
        {seller && <span className="make-sub">via {seller}</span>}
      </div>

      <div className="offer-columns">
        <div className="offer-left">
          <div className="offer-stage">
            <CarGlyph shape={shapeKey} carColor={carColor} />
            <span className="stage-tag">{body_type || "—"}</span>
          </div>

          <div className="offer-title-block">
            <span className="offer-title" title={title}>{title}</span>
            <span className="offer-spec">
              {[
                year,
                mileage_km != null ? `${mileage_km.toLocaleString("de-DE")} km` : null,
                power_hp ? `${power_hp} hp` : null,
                fuel,
                transmission,
              ]
                .filter(Boolean)
                .join(" · ")}
            </span>
          </div>

          <div className="offer-seller-row">
            {seller && <span className="offer-dealer">{seller}</span>}
            {city && <span>{seller ? "· " : ""}{city}</span>}
            {ratings_average != null && (
              <span className="rating-chip">
                <span className="star">★</span> {ratings_average} · {ratings_count} reviews
              </span>
            )}
          </div>

          <div className="fact-chips">
            {had_accident === false && <span className="fact-chip good">No accident</span>}
            {full_service_history && <span className="fact-chip good">Full service history</span>}
            {previous_owners != null && (
              <span className="fact-chip">
                {previous_owners} previous owner{previous_owners === 1 ? "" : "s"}
              </span>
            )}
            {drive_train && <span className="fact-chip">{drive_train}</span>}
            {consumption_l_100km != null && co2_g_km != null ? (
              <span className="fact-chip">{consumption_l_100km} l/100km · {co2_g_km} g CO₂/km</span>
            ) : (
              <span className="fact-chip na">Consumption not provided</span>
            )}
          </div>
        </div>

        <div className="offer-right">
          <div className="price-panel">
            <div className="price-head">
              <span className="price-value">
                {fmtEur(monthly_rate_eur, 2)}
                <span className="unit">/ month</span>
              </span>
              <span className="price-vat">
                incl. VAT · {term_months} months · {annual_km?.toLocaleString("de-DE")} km/year
              </span>
            </div>
            {leasing_factor_pct != null && (
              <span className="lease-factor">{leasing_factor_pct}% of list price / month</span>
            )}

            {comparison && (
              <div className="compare">
                <span className={`verdict-pill verdict-pill--${comparison.direction}`}>
                  {Math.abs(comparison.difference_pct)}%{" "}
                  {comparison.direction === "below"
                    ? "below market"
                    : comparison.direction === "above"
                      ? "above market"
                      : "at market"}
                </span>
                <PriceBar priceEur={price_eur} comparison={comparison} />
                <p className="compare-note">
                  {fmtEur(price_eur)} vs. a median of {fmtEur(comparison.median_price_eur)} across{" "}
                  {comparison.comparables} comparable listings.
                </p>
              </div>
            )}

            <div className="list-price-row">
              <span className="k">List price</span>
              <span className="v">{fmtEur(price_eur)}</span>
            </div>
            <div className="list-price-row list-price-row--plain">
              <span className="k">Down payment</span>
              <span className="v">{fmtEur(down_payment_eur)}</span>
            </div>
          </div>
        </div>
      </div>

      <details className="lease-details">
        <summary>
          Leasing details <span className="chevron">▾</span>
        </summary>
        <div className="lease-groups">
          <div>
            <div className="lease-group-label">Monthly</div>
            <div className="lease-rows">
              <div className="lease-row">
                <span className="k">Depreciation</span>
                <span className="v">{fmtEur(breakdown.depreciation_eur, 2)}</span>
              </div>
              <div className="lease-row">
                <span className="k">Finance charge ({breakdown.apr_pct}% p.a.)</span>
                <span className="v">{fmtEur(breakdown.finance_eur, 2)}</span>
              </div>
              <div className="lease-row">
                <span className="k">Leasing rate</span>
                <span className="v">{fmtEur(monthly_rate_eur, 2)}</span>
              </div>
            </div>
          </div>
          <div>
            <div className="lease-group-label">One-time</div>
            <div className="lease-rows">
              <div className="lease-row">
                <span className="k">Down payment</span>
                <span className="v">{fmtEur(down_payment_eur)}</span>
              </div>
              <div className="lease-row">
                <span className="k">Residual value at term end</span>
                <span className="v">{fmtEur(breakdown.residual_value_eur)}</span>
              </div>
            </div>
          </div>
          <div className="total-box">
            <span className="k">Total cost · {term_months} months</span>
            <span className="v">{fmtEur(total_cost_eur, 2)}</span>
          </div>
          {cost_per_km_eur != null && (
            <div className="per-km-row">
              <span>Cost per km</span>
              <span className="v">{fmtEur(cost_per_km_eur, 2)}/km</span>
            </div>
          )}
        </div>
      </details>

      {footnote && <p className="offer-footnote">{footnote}</p>}
    </div>
  );
}

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
  if (payload.type === "offer") {
    return (
      <div className="panel">
        <OfferCard payload={payload} />
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
  // Filter-panel state is separate from `payload`: "filters" messages update
  // which body-type icon is lit without touching whatever card (cars/quote/
  // offer) is currently showing, since both can arrive from the same turn.
  const [activeFilters, setActiveFilters] = useState(null);
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
      let parsed;
      try {
        parsed = JSON.parse(text);
      } catch {
        setPayload({ type: "text", text });
        return;
      }
      if (parsed.type === "filters") {
        setActiveFilters(parsed);
      } else {
        setPayload(parsed);
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
      <CarTypeFilterPanel active={activeFilters} />
      <ToolPanel payload={payload} />
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
