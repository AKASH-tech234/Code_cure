"use client";

import { motion } from "framer-motion";
import {
  Activity,
  ArrowRight,
  Globe,
  LineChart,
  Network,
  Radar,
  Shield,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, PointMaterial, Points } from "@react-three/drei";
import type { LucideIcon } from "lucide-react";
import * as THREE from "three";

type Capability = {
  title: string;
  desc: string;
  icon: LucideIcon;
};

const capabilities: Capability[] = [
  {
    title: "Outbreak Prediction",
    desc: "SEIR/SIR-informed forecasting for short horizon demand and policy stress checks.",
    icon: LineChart,
  },
  {
    title: "Hotspot Detection",
    desc: "Risk scoring from mobility, growth, vaccination, and pressure indicators.",
    icon: Radar,
  },
  {
    title: "Transmission Graph",
    desc: "Network-oriented spread reasoning to identify likely acceleration pathways.",
    icon: Network,
  },
  {
    title: "Resilience Signals",
    desc: "Intervention impact tracking to detect recovery momentum and drag factors.",
    icon: Shield,
  },
];

function StarField() {
  const pointsRef = useRef<THREE.Points>(null);

  const positions = useMemo(() => {
    const count = 150;
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i += 1) {
      pos[i * 3] = (Math.random() - 0.5) * 32;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 20;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 24 - 6;
    }
    return pos;
  }, []);

  useFrame((state) => {
    if (!pointsRef.current) {
      return;
    }

    const t = state.clock.getElapsedTime();
    pointsRef.current.rotation.y = t * 0.03;
    pointsRef.current.rotation.x = Math.sin(t * 0.2) * 0.06;
  });

  return (
    <Points ref={pointsRef} positions={positions} stride={3}>
      <PointMaterial
        transparent
        color="#b8fff2"
        size={0.06}
        sizeAttenuation
        depthWrite={false}
        opacity={0.45}
      />
    </Points>
  );
}

function EpidemicOrbs() {
  const groupRef = useRef<THREE.Group>(null);

  const nodes = useMemo(() => {
    const total = 78;
    return Array.from({ length: total }, (_, idx) => {
      const phi = Math.acos(-1 + (2 * idx) / total);
      const theta = Math.sqrt(total * Math.PI) * phi;
      const radius = 3.2 + Math.sin(idx * 0.35) * 0.5;
      return {
        idx,
        position: [
          radius * Math.cos(theta) * Math.sin(phi),
          radius * Math.sin(theta) * Math.sin(phi),
          radius * Math.cos(phi),
        ] as [number, number, number],
      };
    });
  }, []);

  useFrame((state) => {
    if (!groupRef.current) {
      return;
    }

    const t = state.clock.getElapsedTime();
    groupRef.current.rotation.y = t * 0.16;
    groupRef.current.rotation.x = Math.sin(t * 0.3) * 0.1;
  });

  return (
    <>
      <group ref={groupRef}>
        {nodes.map((node) => {
          const infected = node.idx % 8 === 0;
          const recovered = !infected && node.idx % 5 === 0;
          const color = infected
            ? "#ff4d5a"
            : recovered
              ? "#42f59e"
              : "#5cb7ff";
          const scale = infected ? 0.13 : 0.1;

          return (
            <mesh key={`orb-${node.idx}`} position={node.position}>
              <sphereGeometry args={[scale, 12, 12]} />
              <meshStandardMaterial
                color={color}
                emissive={color}
                emissiveIntensity={infected ? 0.52 : 0.18}
              />
            </mesh>
          );
        })}
      </group>
      <mesh>
        <torusGeometry args={[4.35, 0.02, 10, 160]} />
        <meshBasicMaterial color="#2df9d7" transparent opacity={0.35} />
      </mesh>
    </>
  );
}

function SimulationScene() {
  return (
    <Canvas camera={{ position: [0, 0, 10], fov: 46 }} dpr={[1, 1.5]}>
      <ambientLight intensity={0.7} />
      <directionalLight position={[6, 8, 6]} intensity={1.2} />
      <pointLight position={[-4, -1, 3]} intensity={1.05} color="#1ef5cf" />
      <StarField />
      <EpidemicOrbs />
      <OrbitControls
        enablePan={false}
        enableZoom={false}
        autoRotate
        autoRotateSpeed={0.4}
      />
    </Canvas>
  );
}

export default function LandingClient() {
  return (
    <main className="min-h-screen bg-[#070b11] text-slate-100">
      <section className="relative mx-auto grid min-h-screen max-w-7xl grid-cols-1 items-center gap-14 px-6 py-24 lg:grid-cols-[1.08fr_1fr] lg:px-10">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_8%_8%,rgba(39,247,218,0.14),transparent_36%),radial-gradient(circle_at_90%_80%,rgba(65,140,255,0.15),transparent_32%)]" />

        <div className="space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65 }}
            className="inline-flex items-center gap-2 rounded-full border border-cyan-300/25 bg-cyan-300/10 px-4 py-1 text-[10px] font-semibold uppercase tracking-[0.35em] text-cyan-200"
          >
            <Activity className="h-3.5 w-3.5" />
            Surveillance Grid
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 26 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.75, delay: 0.08 }}
            className="text-5xl font-black leading-[0.9] tracking-tight text-white font-[Space_Grotesk,ui-sans-serif,system-ui] sm:text-6xl lg:text-7xl"
          >
            Advanced
            <span className="block bg-linear-to-r from-cyan-300 via-teal-200 to-emerald-200 bg-clip-text text-transparent">
              Epidemic Defense
            </span>
            Platform
          </motion.h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.22 }}
            className="max-w-xl text-base leading-relaxed text-slate-300 sm:text-lg"
          >
            Predict spread, evaluate risk, and test interventions through one
            high-fidelity intelligence stack served via the existing ml-service
            boundary.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.32 }}
            className="flex flex-wrap gap-3"
          >
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-sm bg-linear-to-r from-cyan-300 to-teal-200 px-6 py-3 text-sm font-bold uppercase tracking-[0.12em] text-slate-900 shadow-[0_0_25px_rgba(56,232,217,0.28)] transition hover:scale-[1.02]"
            >
              Enter Testing Frontend
              <ArrowRight className="h-4 w-4" />
            </Link>

            <Link
              href="/chat"
              className="inline-flex items-center rounded-sm border border-slate-500/60 px-6 py-3 text-sm font-semibold uppercase tracking-[0.12em] text-slate-200 transition hover:border-cyan-300/60 hover:text-white"
            >
              Open Chat
            </Link>
          </motion.div>

          <p className="pt-2 text-xs uppercase tracking-[0.2em] text-slate-400">
            Model priority source: Epidemic_Spread_Prediction to ml-service
            adapter
          </p>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.0, delay: 0.2 }}
          className="relative h-107.5 overflow-hidden rounded-2xl border border-cyan-300/20 bg-slate-900/40 shadow-[0_0_60px_rgba(20,247,216,0.08)] lg:h-140"
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(45,249,215,0.12),transparent_45%)]" />
          <div className="absolute inset-0">
            <SimulationScene />
          </div>
        </motion.div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-24 lg:px-10">
        <div className="mb-8 flex items-center justify-between gap-4">
          <h2 className="text-2xl font-bold tracking-tight text-white font-[Space_Grotesk,ui-sans-serif,system-ui] sm:text-3xl">
            Core Capabilities
          </h2>
          <div className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-slate-300">
            <Globe className="h-4 w-4 text-cyan-300" />
            Global Coverage
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {capabilities.map((item, idx) => (
            <motion.article
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-30px" }}
              transition={{ duration: 0.52, delay: idx * 0.08 }}
              className="rounded-xl border border-slate-700/60 bg-slate-900/50 p-5 transition hover:border-cyan-300/35"
            >
              <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-md bg-cyan-300/15 text-cyan-200">
                <item.icon className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-bold text-white">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">
                {item.desc}
              </p>
            </motion.article>
          ))}
        </div>
      </section>
    </main>
  );
}
