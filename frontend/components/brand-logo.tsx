import Image from "next/image";
import Link from "next/link";

export function BrandLogo({ compact = false }: { compact?: boolean }) {
  return (
    <Link className="group flex items-center gap-3" href="/app" aria-label="Terbb Scale">
      <span className="brand-mark">
        <Image
          className="scale-[1.72] object-cover"
          src="/terbb-scale.png"
          alt=""
          width={52}
          height={52}
          priority
        />
      </span>
      {!compact && (
        <span className="text-[17px] font-bold tracking-[-0.025em] text-white">
          TERBB <span className="text-violet-400">SCALE</span>
        </span>
      )}
    </Link>
  );
}
