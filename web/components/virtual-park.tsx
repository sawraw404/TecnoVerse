"use client";

// Stylised 3D virtual science park for the staff knowledge graph. Loaded only in the browser
// (next/dynamic with ssr: false) and only when the user switches to 3D, so three.js stays out of the
// main bundle. A diagram, not a map: Blue Science Park is the central island, each park focus area an
// island around it, each company a building on its area's island.
import { OrbitControls, QuadraticBezierLine, RoundedBox } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import type { EdgeKind, Graph, GraphEdge } from "@/lib/types";

type IndexedEdge = GraphEdge & { i: number };

export interface VirtualParkProps {
  graph: Graph;
  edges: IndexedEdge[]; // already filtered by the link toggles
  dimmed: (id: string) => boolean;
  highlighted: Set<string>;
  selectedId: string | null;
  selectedEdge: number | null;
  onSelectNode: (id: string | null) => void;
  onSelectEdge: (i: number) => void;
  onHover: (id: string | null) => void;
}

/** Theme colours come from the CSS tokens, so the 3D scene follows light and dark mode. */
function useTheme() {
  const read = () => {
    const cs = getComputedStyle(document.documentElement);
    const v = (n: string) => cs.getPropertyValue(n).trim() || "#888888";
    return {
      bg: v("--bg"),
      surface: v("--surface"),
      text: v("--text"),
      primary: v("--primary"),
      blue: v("--blue"),
      water: v("--nav-2"),
      area: (a: string | null) => v(`--area-${a ?? "other"}`),
    };
  };
  const [theme, setTheme] = useState(read);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setTheme(read());
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return theme;
}

const PARK_RADIUS = 6;
const RING = 26; // distance of the area islands from the centre

interface Placed {
  id: string;
  x: number;
  z: number;
  h: number; // building height
}

/** Islands per focus area (bigger sector and island for bigger areas) and buildings on them. */
function useLayout(graph: Graph) {
  return useMemo(() => {
    const companies = graph.nodes.filter((n) => n.kind === "company");
    const links = new Map<string, number>();
    for (const e of graph.edges) {
      if (e.kind === "collaboration" || e.kind === "suggestion") {
        links.set(e.source, (links.get(e.source) ?? 0) + 1);
        links.set(e.target, (links.get(e.target) ?? 0) + 1);
      }
    }
    const areas = Object.keys(graph.areas);
    const count = (a: string) => companies.filter((c) => c.area === a).length;
    const total = areas.reduce((t, a) => t + count(a) + 3, 0);
    let acc = -Math.PI / 2;
    const islands = areas.map((a) => {
      const share = ((count(a) + 3) / total) * Math.PI * 2;
      const angle = acc + share / 2;
      acc += share;
      const r = 3.2 + Math.sqrt(count(a)) * 1.9;
      return { area: a, label: graph.areas[a], x: Math.cos(angle) * RING, z: Math.sin(angle) * RING, r };
    });
    const buildings: Placed[] = [];
    for (const isl of islands) {
      // members first, so they sit in the middle of the island; phyllotaxis spreads buildings evenly
      const list = companies.filter((c) => c.area === isl.area).sort((a, b) => Number(b.member) - Number(a.member));
      list.forEach((c, k) => {
        const rr = list.length === 1 ? 0 : 1.9 * Math.sqrt(k + 0.5);
        const t = k * 2.39996;
        buildings.push({
          id: c.id,
          x: isl.x + Math.cos(t) * rr,
          z: isl.z + Math.sin(t) * rr,
          h: 1.4 + (links.get(c.id) ?? 0) * 0.9 + (c.member ? 0.8 : 0),
        });
      });
    }
    return { islands, buildings: new Map(buildings.map((b) => [b.id, b])) };
  }, [graph]);
}

/** Flies the orbit target (and camera) to the selected building; jumps when motion is reduced. */
function Rig({ target }: { target: THREE.Vector3 | null }) {
  const { camera, controls } = useThree();
  const goal = useRef<{ t: THREE.Vector3; c: THREE.Vector3 } | null>(null);
  const reduce = useMemo(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches, []);
  useEffect(() => {
    if (!target) return;
    const offset = new THREE.Vector3(10, 11, 14);
    goal.current = { t: target.clone(), c: target.clone().add(offset) };
  }, [target]);
  useFrame(() => {
    const ctl = controls as unknown as OrbitControlsImpl | null;
    if (!goal.current || !ctl) return;
    const k = reduce ? 1 : 0.08;
    ctl.target.lerp(goal.current.t, k);
    camera.position.lerp(goal.current.c, k);
    ctl.update();
    if (camera.position.distanceTo(goal.current.c) < 0.05) goal.current = null;
  });
  return null;
}

const EDGE_STYLE: Record<Extract<EdgeKind, "collaboration" | "suggestion">, { width: number; dashed: boolean }> = {
  collaboration: { width: 3, dashed: false },
  suggestion: { width: 2, dashed: true },
};

/** A text label drawn onto a canvas texture and shown as a sprite that always faces the camera.
 *  (drei's Html gives every label its own React root, which with React 19 drops the first label and
 *  logs an error per label on unmount; a sprite needs no DOM at all.) */
function Label({
  text,
  sub,
  position,
  fg,
  bg,
  border,
  visible = true,
  size = 1,
}: {
  text: string;
  sub?: string;
  position: [number, number, number];
  fg: string;
  bg: string;
  border?: string;
  visible?: boolean;
  size?: number;
}) {
  const { texture, aspect } = useMemo(() => {
    const scale = 3; // draw at 3x for sharp text
    const font = getComputedStyle(document.body).fontFamily || "sans-serif";
    const c = document.createElement("canvas");
    const ctx = c.getContext("2d")!;
    const main = `600 ${13 * scale}px ${font}`;
    const small = `500 ${11 * scale}px ${font}`;
    ctx.font = main;
    const wMain = ctx.measureText(text).width;
    ctx.font = small;
    const wSub = sub ? ctx.measureText(sub).width + 8 * scale : 0;
    const padX = 9 * scale;
    c.width = Math.ceil(wMain + wSub + padX * 2);
    c.height = 26 * scale;
    ctx.fillStyle = bg;
    ctx.strokeStyle = border ?? bg;
    ctx.lineWidth = 2 * scale;
    ctx.beginPath();
    ctx.roundRect(scale, scale, c.width - 2 * scale, c.height - 2 * scale, 8 * scale);
    ctx.fill();
    ctx.stroke();
    ctx.textBaseline = "middle";
    ctx.font = main;
    ctx.fillStyle = fg;
    ctx.fillText(text, padX, c.height / 2 + scale);
    if (sub) {
      ctx.font = small;
      ctx.globalAlpha = 0.65;
      ctx.fillText(sub, padX + wMain + 8 * scale, c.height / 2 + scale);
    }
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 4;
    return { texture: t, aspect: c.width / c.height };
  }, [text, sub, fg, bg, border]);
  useEffect(() => () => texture.dispose(), [texture]);
  const h = 0.03 * size; // fraction of the view height: labels keep the same size on screen at any zoom
  return (
    <sprite position={position} scale={[h * aspect, h, 1]} renderOrder={10} visible={visible}>
      <spriteMaterial map={texture} transparent depthTest={false} depthWrite={false} sizeAttenuation={false} />
    </sprite>
  );
}

function Scene(p: VirtualParkProps & { theme: ReturnType<typeof useTheme> }) {
  const { graph, theme } = p;
  const { islands, buildings } = useLayout(graph);
  const [hover, setHover] = useState<string | null>(null);
  const sel = p.selectedId ? buildings.get(p.selectedId) : undefined;
  const target = useMemo(() => (sel ? new THREE.Vector3(sel.x, sel.h / 2, sel.z) : null), [sel]);
  const showMembers = p.edges.some((e) => e.kind === "member");

  return (
    <>
      <color attach="background" args={[theme.bg]} />
      <fog attach="fog" args={[theme.bg, 70, 150]} />
      <hemisphereLight args={["#ffffff", theme.water, 0.9]} />
      <directionalLight position={[30, 50, 20]} intensity={1.6} castShadow shadow-mapSize={[2048, 2048]}>
        <orthographicCamera attach="shadow-camera" args={[-50, 50, 50, -50, 1, 150]} />
      </directionalLight>

      {/* water */}
      <mesh rotation-x={-Math.PI / 2} position-y={-0.05} receiveShadow onClick={() => p.onSelectNode(null)}>
        <circleGeometry args={[110, 96]} />
        <meshStandardMaterial color={theme.water} roughness={0.35} metalness={0.1} />
      </mesh>

      {/* Blue Science Park: central island and tower */}
      <group onClick={(e) => (e.stopPropagation(), p.onSelectNode("bsp"))}>
        <mesh position-y={0.3} receiveShadow>
          <cylinderGeometry args={[PARK_RADIUS, PARK_RADIUS + 0.6, 0.6, 64]} />
          <meshStandardMaterial color={theme.surface} roughness={0.9} />
        </mesh>
        <mesh position-y={0.62} rotation-x={-Math.PI / 2}>
          <ringGeometry args={[PARK_RADIUS - 0.45, PARK_RADIUS, 96]} />
          <meshBasicMaterial color={theme.primary} />
        </mesh>
        <mesh position-y={5.6} castShadow>
          <cylinderGeometry args={[1.6, 2.2, 10, 6]} />
          <meshStandardMaterial color={theme.primary} roughness={0.25} metalness={0.3} transparent opacity={0.92} />
        </mesh>
        <mesh position-y={10.9}>
          <torusGeometry args={[2.6, 0.12, 12, 64]} />
          <meshStandardMaterial color={theme.primary} emissive={theme.primary} emissiveIntensity={0.8} />
        </mesh>
        <Label text="Blue Science Park" position={[0, 13.6, 0]} fg="#ffffff" bg={theme.primary} size={1.25} />
      </group>

      {/* focus-area islands */}
      {islands.map((isl) => (
        <group key={isl.area} position={[isl.x, 0, isl.z]}>
          <mesh position-y={0.25} receiveShadow onClick={(e) => (e.stopPropagation(), p.onSelectNode(`area:${isl.area}`))}>
            <cylinderGeometry args={[isl.r, isl.r + 0.7, 0.5, 48]} />
            <meshStandardMaterial color={theme.surface} roughness={0.95} />
          </mesh>
          <mesh position-y={0.52} rotation-x={-Math.PI / 2}>
            <ringGeometry args={[isl.r - 0.35, isl.r, 64]} />
            <meshBasicMaterial color={theme.area(isl.area)} />
          </mesh>
          <Label text={isl.label} position={[0, 1.6, isl.r + 2.4]} fg={theme.area(isl.area)} bg={theme.surface} border={theme.area(isl.area)} size={1.05} />
        </group>
      ))}

      {/* membership: a faint path from each member building to the park */}
      {showMembers &&
        graph.nodes
          .filter((n) => n.kind === "company" && n.member)
          .map((n) => {
            const b = buildings.get(n.id)!;
            return (
              <QuadraticBezierLine
                key={`m-${n.id}`}
                start={[b.x, 0.56, b.z]}
                end={[0, 0.66, 0]}
                mid={[b.x / 2, 0.6, b.z / 2]}
                color={theme.primary}
                lineWidth={1}
                transparent
                opacity={p.dimmed(n.id) ? 0.05 : 0.3}
              />
            );
          })}

      {/* company buildings */}
      {graph.nodes
        .filter((n) => n.kind === "company")
        .map((n) => {
          const b = buildings.get(n.id)!;
          const c = theme.area(n.area);
          const lit = p.highlighted.has(n.id) || hover === n.id || p.selectedId === n.id;
          const off = p.dimmed(n.id);
          return (
            <group key={n.id} position={[b.x, 0.5, b.z]}>
              <RoundedBox
                args={[1.5, b.h, 1.5]}
                radius={0.12}
                position-y={b.h / 2}
                castShadow
                receiveShadow
                onPointerOver={(e) => (e.stopPropagation(), setHover(n.id), p.onHover(n.id), (document.body.style.cursor = "pointer"))}
                onPointerOut={() => (setHover(null), p.onHover(null), (document.body.style.cursor = ""))}
                onClick={(e) => (e.stopPropagation(), p.onSelectNode(n.id))}
              >
                {n.member ? (
                  <meshStandardMaterial
                    color={c}
                    roughness={0.45}
                    metalness={0.15}
                    emissive={c}
                    emissiveIntensity={lit ? 0.55 : 0.08}
                    transparent
                    opacity={off ? 0.15 : 1}
                  />
                ) : (
                  <meshPhysicalMaterial
                    color={c}
                    roughness={0.1}
                    transmission={0.6}
                    thickness={0.8}
                    emissive={c}
                    emissiveIntensity={lit ? 0.5 : 0.04}
                    transparent
                    opacity={off ? 0.1 : 0.55}
                  />
                )}
              </RoundedBox>
              <Label
                text={n.label}
                sub={n.member ? "member" : "external"}
                position={[0, b.h + 1.8, 0]}
                fg={theme.text}
                bg={theme.surface}
                border={theme.area(n.area)}
                visible={lit}
              />
            </group>
          );
        })}

      {/* collaborations and suggested connections: arcs between rooftops */}
      {p.edges
        .filter((e): e is IndexedEdge & { kind: "collaboration" | "suggestion" } => e.kind === "collaboration" || e.kind === "suggestion")
        .map((e) => {
          const a = buildings.get(e.source);
          const b = buildings.get(e.target);
          if (!a || !b) return null;
          const st = EDGE_STYLE[e.kind];
          const off = p.dimmed(e.source) || p.dimmed(e.target);
          const active = p.selectedEdge === e.i;
          const start: [number, number, number] = [a.x, a.h + 0.5, a.z];
          const end: [number, number, number] = [b.x, b.h + 0.5, b.z];
          const lift = Math.hypot(a.x - b.x, a.z - b.z) * 0.35 + 3;
          return (
            <QuadraticBezierLine
              key={`e-${e.i}`}
              start={start}
              end={end}
              mid={[(a.x + b.x) / 2, Math.max(a.h, b.h) + lift, (a.z + b.z) / 2]}
              color={e.kind === "suggestion" ? theme.blue : theme.text}
              lineWidth={active ? st.width + 2 : st.width}
              dashed={st.dashed}
              dashSize={0.7}
              gapSize={0.45}
              transparent
              opacity={off ? 0.06 : 0.9}
              onClick={(ev) => (ev.stopPropagation(), p.onSelectEdge(e.i))}
              onPointerOver={() => (document.body.style.cursor = "pointer")}
              onPointerOut={() => (document.body.style.cursor = "")}
            />
          );
        })}

      <OrbitControls
        makeDefault
        enableDamping
        dampingFactor={0.08}
        minDistance={12}
        maxDistance={120}
        maxPolarAngle={Math.PI / 2.15}
      />
      <Rig target={target} />
    </>
  );
}

function hasWebGL() {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

export default function VirtualPark(props: VirtualParkProps) {
  const theme = useTheme();
  const [webgl] = useState(hasWebGL);
  if (!webgl) {
    return (
      <div className="grid aspect-[4/3] w-full place-items-center bg-surface-2 p-6 text-center text-sm text-text-2">
        This browser cannot show 3D graphics (WebGL is off). The 2D view and the list below show the same information.
      </div>
    );
  }
  return (
    <div className="relative aspect-[4/3] w-full" role="img" aria-label="3D virtual science park. The list below the view has the same information.">
      <Canvas
        shadows="percentage"
        dpr={[1, 2]}
        camera={{ position: [0, 62, 80], fov: 42 }}
        onPointerMissed={() => props.onSelectNode(null)}
      >
        <Scene {...props} theme={theme} />
      </Canvas>
      <p className="pointer-events-none absolute bottom-2 left-3 text-[11px] text-text-3">
        Stylised view, not a map · drag to rotate, right-drag to pan, scroll to zoom
      </p>
    </div>
  );
}
