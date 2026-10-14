/** Decorative network of nodes and links. One signal travels along a single path (the page's one moving element).
 *  Coordinates are fixed so the artwork is identical on every render; it is hidden from assistive technology. */
const NODES: [number, number][] = [
  [40, 70], [120, 30], [200, 90], [290, 40], [370, 100], [450, 50],
  [70, 170], [160, 150], [250, 190], [340, 160], [430, 200], [520, 140],
  [30, 270], [130, 250], [220, 290], [310, 260], [410, 300], [500, 250],
];
const LINKS: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [0, 6], [1, 7], [2, 7], [2, 8], [3, 9], [4, 9], [4, 10], [5, 11],
  [6, 7], [7, 8], [8, 9], [9, 10], [10, 11], [6, 12], [7, 13], [8, 14], [9, 15], [10, 16], [11, 17],
  [12, 13], [13, 14], [14, 15], [15, 16], [16, 17],
];
const SIGNAL = 'M40 70 L120 30 L200 90 L250 190 L340 160 L430 200 L520 140';

export function NeuralField({ className = '' }: { className?: string }) {
  return (
    <svg className={`neural ${className}`} viewBox="0 0 560 320" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
      <g className="neural-links">{LINKS.map(([a, b], i) => <line key={i} x1={NODES[a][0]} y1={NODES[a][1]} x2={NODES[b][0]} y2={NODES[b][1]} />)}</g>
      <g className="neural-nodes">{NODES.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={i % 5 === 0 ? 5 : 3.5} />)}</g>
      <path className="neural-signal" d={SIGNAL} pathLength={100} />
      <circle className="neural-spark" r="6"><animateMotion dur="7s" repeatCount="indefinite" path={SIGNAL} /></circle>
    </svg>
  );
}
