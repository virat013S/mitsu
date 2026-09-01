import { cn } from "@/lib/utils";

export type MitsuState = string;

export function Reactor({ state }: { state: MitsuState }) {
  return (
    <div className={cn("reactor", `reactor-${state.toLowerCase()}`)} aria-label={`MITSU state: ${state}`} role="img">
      <div className="reactor-orbit orbit-a" />
      <div className="reactor-orbit orbit-b" />
      <div className="reactor-spokes" />
      <div className="reactor-core"><span>M</span></div>
    </div>
  );
}
