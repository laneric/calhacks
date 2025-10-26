// components/DitherField.tsx
'use client';

import { useEffect, useRef } from 'react';

type WaveDir = 'lr' | 'rl' | 'tb' | 'bt' | 'diag' | 'radial';

type Props = {
  cell?: number;
  smallMin?: number;
  smallMax?: number;
  bigScale?: number;
  bigDotChance?: number;
  dotColor?: string;
  blobCount?: number;
  minBlobSize?: number;
  maxBlobSize?: number;
  speed?: number;
  density?: number;
  warpAmount?: number;
  isVisible?: boolean;

  offWaveDirection?: WaveDir;
  offWaveDurationMs?: number;
  offWaveSigma?: number;
  offWaveTailMs?: number;
};

export default function DitherField({
  cell = 10,
  smallMin = 0.22,
  smallMax = 1,
  bigScale = 1.28,
  bigDotChance = 0.1,
  dotColor = '#FFFFFF',
  blobCount = 9,
  minBlobSize = 0.05,
  maxBlobSize = 0.4,
  speed = 0.3,
  density = 1.0,
  warpAmount = 0.1,
  isVisible = true,

  offWaveDirection = 'lr',
  offWaveDurationMs = 400,
  offWaveSigma = 0.2,
  offWaveTailMs = 60,
}: Props) {
  const ref = useRef<HTMLCanvasElement>(null);

  const modeRef = useRef<'on' | 'wave-off' | 'hidden'>(isVisible ? 'on' : 'hidden');
  const waveStartRef = useRef<number | null>(null);

  useEffect(() => {
    if (isVisible) {
      modeRef.current = 'on';
      waveStartRef.current = null;
    } else if (modeRef.current === 'on') {
      modeRef.current = 'wave-off';
      waveStartRef.current = performance.now();
    }
  }, [isVisible]);

  useEffect(() => {
    const canvas = ref.current!;
    const ctx = canvas.getContext('2d', { alpha: true })!;

    // double buffer
    let back: HTMLCanvasElement | OffscreenCanvas;
    let bctx: OffscreenCanvasRenderingContext2D | CanvasRenderingContext2D;

    const setup = () => {
      const dpr = Math.max(1, window.devicePixelRatio || 1);
      const w = Math.floor(window.innerWidth);
      const h = Math.floor(window.innerHeight);

      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      try {
        // @ts-ignore
        back = new OffscreenCanvas(w * dpr, h * dpr);
        // @ts-ignore
        bctx = back.getContext('2d', { alpha: true })!;
      } catch {
        const c = document.createElement('canvas');
        c.width = w * dpr; c.height = h * dpr;
        back = c;
        bctx = c.getContext('2d', { alpha: true })!;
      }
      // @ts-ignore
      bctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    setup();
    const onResize = () => setup();
    window.addEventListener('resize', onResize);

    // helpers
    const hash = (x: number, y: number, s = 0) => {
      const n = Math.sin(x * 127.1 + y * 311.7 + s * 17.23) * 43758.5453;
      return n - Math.floor(n);
    };
    const key = (i: number, j: number) => `${i},${j}`;

    const jitter = new Map<string, { jx: number; jy: number }>();
    const bigPick = new Map<string, number>();
    function ensureCell(i: number, j: number) {
      const k = key(i, j);
      if (!jitter.has(k)) {
        const jx = (hash(i, j, 1) - 0.5) * 0.35;
        const jy = (hash(i, j, 2) - 0.5) * 0.35;
        jitter.set(k, { jx, jy });
        bigPick.set(k, hash(i, j, 3));
      }
    }

    function vnoise(x: number, y: number, s = 0) {
      const xi = Math.floor(x), yi = Math.floor(y);
      const xf = x - xi, yf = y - yi;
      const h00 = hash(xi, yi, s);
      const h10 = hash(xi + 1, yi, s);
      const h01 = hash(xi, yi + 1, s);
      const h11 = hash(xi + 1, yi + 1, s);
      const ux = xf * xf * (3 - 2 * xf);
      const uy = yf * yf * (3 - 2 * yf);
      const x1 = h00 * (1 - ux) + h10 * ux;
      const x2 = h01 * (1 - ux) + h11 * ux;
      return x1 * (1 - uy) + x2 * uy;
    }
    function fbm(x: number, y: number, t: number) {
      let v = 0, amp = 0.5, fx = x, fy = y;
      for (let o = 0; o < 4; o++) {
        v += amp * vnoise(fx + t * 0.03, fy - t * 0.025, o * 11.7);
        fx *= 2.02; fy *= 2.02; amp *= 0.5;
      }
      return v;
    }

    const blobs = Array.from({ length: blobCount }).map((_, k) => {
      const size = minBlobSize + (maxBlobSize - minBlobSize) * hash(k + 5, 0);
      return {
        size,
        wx: 0.32 + 0.86 * hash(k + 1, 0),
        wy: 0.32 + 0.86 * hash(k + 2, 0),
        fx: 0.35 + 0.9 * hash(k + 3, 0),
        fy: 0.35 + 0.9 * hash(k + 4, 0),
        phx: 6.283 * hash(k + 6, 0),
        phy: 6.283 * hash(k + 7, 0),
        strength: 0.7 + 0.8 * hash(k + 8, 0),
        speedMul: 0.6 + 1.6 * hash(k + 9, 0),
      };
    });

    const smoothstep = (a: number, b: number, x: number) => {
      const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
      return t * t * (3 - 2 * t);
    };

    function baseField(nx: number, ny: number, t: number) {
      const wx = fbm(nx * 3.2, ny * 3.2, t) - 0.5;
      const wy = fbm(nx * 3.2 + 7.1, ny * 3.2 - 4.3, t) - 0.5;
      const x = nx + warpAmount * wx;
      const y = ny + warpAmount * wy;

      let v = 0;
      for (let k = 0; k < blobs.length; k++) {
        const b = blobs[k];
        const cx = 0.5 + b.wx * Math.sin(t * b.fx * b.speedMul * speed + b.phx) - 0.325;
        const cy = 0.5 + b.wy * Math.cos(t * b.fy * b.speedMul * speed + b.phy) - 0.325;
        const dx = x - cx, dy = y - cy;
        const r2 = b.size * b.size * (0.85 + 0.3 * vnoise(x * 5.0 + k, y * 5.0 - k, 21.7));
        v += b.strength * Math.exp(-(dx * dx + dy * dy) / r2);
      }
      return Math.min(1, v * 0.9 * density);
    }

    const waveCoord = (nx: number, ny: number) => {
      switch (offWaveDirection) {
        case 'lr': return nx;
        case 'rl': return 1 - nx;
        case 'tb': return ny;
        case 'bt': return 1 - ny;
        case 'diag': return (nx + ny) * 0.5;
        case 'radial': {
          const dx = nx - 0.5, dy = ny - 0.5;
          return Math.min(1, Math.sqrt(dx * dx + dy * dy) / Math.SQRT1_2);
        }
      }
    };

    let raf = 0;
    function render(ts: number) {
      const w = canvas.clientWidth, h = canvas.clientHeight;

      const mode = modeRef.current;
      const t = ts / 1000;
      const t0 = waveStartRef.current;
      const waveActive = mode === 'wave-off' && t0 != null;

      // head position is NOT clamped
      const head = waveActive ? (ts - t0) / offWaveDurationMs : 0;
      const sigma = Math.max(1e-4, offWaveSigma);
      const tau = Math.max(16, offWaveTailMs);

      // pre-compute an upper bound on amplitude inside the viewport
      // pick the worst case inside [0,1] for u given current head
      const uStar = Math.min(1, Math.max(0, head)); // closest point to head inside screen
      const spatialBound = Math.exp(-0.5 * ((uStar - head) / sigma) ** 2);
      const temporalBound = head > uStar ? Math.exp(-((head - uStar) * offWaveDurationMs) / tau) : 1;
      // edge-kill goes to zero once head > 1
      const edgeKill = head <= 1 ? 1 : 1 - smoothstep(1, 1 + 2 * sigma, head);
      const peakInView = waveActive ? spatialBound * temporalBound * edgeKill : 0;

      // if the bound is tiny, hide immediately at frame start
      if (waveActive && peakInView < 0.01) {
        modeRef.current = 'hidden';
      }

      // backbuffer prep
      // @ts-ignore
      bctx.globalCompositeOperation = 'source-over';
      // @ts-ignore
      bctx.globalAlpha = 1;
      // @ts-ignore
      bctx.clearRect(0, 0, w, h);
      // @ts-ignore
      bctx.save();
      // @ts-ignore
      bctx.translate(0.5, 0.5);
      // @ts-ignore
      bctx.fillStyle = dotColor;

      const cols = Math.ceil(w / cell);
      const rows = Math.ceil(h / cell);

      if (modeRef.current !== 'hidden') {
        for (let j = 0; j < rows; j++) {
          for (let i = 0; i < cols; i++) {
            ensureCell(i, j);
            const { jx, jy } = jitter.get(key(i, j))!;
            const px = i * cell + jx;
            const py = j * cell + jy;

            const nx = px / w, ny = py / h;

            let v: number;
            if (mode === 'on') {
              v = baseField(nx, ny, t);
            } else if (waveActive) {
              const u = waveCoord(nx, ny);
              const dx = u - head;                      // head not clamped
              const spatial = Math.exp(-0.5 * (dx / sigma) * (dx / sigma));
              const passedMs = (head - u) * offWaveDurationMs;
              const temporal = passedMs > 0 ? Math.exp(-passedMs / tau) : 1;
              // edge-kill fades to zero right after the head passes 1.0
              const ek = head <= 1 ? 1 : 1 - smoothstep(1, 1 + 2 * sigma, head);
              v = spatial * temporal * ek;
            } else {
              continue;
            }

            const e = (() => {
              const s = Math.max(0, Math.min(1, (v - 0.2) / (0.9 - 0.2)));
              return s * s * (3 - 2 * s);
            })();
            if (e < 0.02) continue;

            const isBig = v > 0.7 && bigPick.get(key(i, j))! > 1 - bigDotChance;
            const rSmall = smallMin + (smallMax - smallMin) * e;
            const r = isBig ? rSmall * bigScale : rSmall;

            let a = isBig ? 1 : 0.5;
            if (waveActive) a *= v;
            if (a <= 0.01) continue;

            // @ts-ignore
            bctx.globalAlpha = a;
            // @ts-ignore
            bctx.beginPath();
            // @ts-ignore
            bctx.arc(px, py, r, 0, Math.PI * 2);
            // @ts-ignore
            bctx.fill();
          }
        }
      }
      // @ts-ignore
      bctx.restore();

      // blit with copy to avoid stale alpha
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'copy';
      // @ts-ignore
      ctx.drawImage(back, 0, 0, canvas.width, canvas.height, 0, 0, w, h);
      ctx.globalCompositeOperation = 'source-over';

      raf = requestAnimationFrame(render);
    }

    raf = requestAnimationFrame(render);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
    };
  }, [
    cell, smallMin, smallMax, bigScale, bigDotChance, dotColor,
    blobCount, minBlobSize, maxBlobSize, speed, density, warpAmount,
    offWaveDirection, offWaveDurationMs, offWaveSigma, offWaveTailMs
  ]);

  return (
    <canvas
      ref={ref}
      className="pointer-events-none fixed inset-0 z-1 mix-blend-screen"
      aria-hidden
    />
  );
}