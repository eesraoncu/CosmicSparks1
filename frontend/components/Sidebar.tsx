import { MapPinIcon, EnvelopeIcon, UserCircleIcon } from "@heroicons/react/24/outline";
import Link from "next/link";


interface SidebarProps {
  onChangeView: (view: string) => void; 
}

export default function Sidebar({ onChangeView }: SidebarProps) {
  return (
    <div className="w-80 h-screen bg-gradient-to-b from-slate-800 via-slate-700 to-slate-900 text-slate-100 flex flex-col border-r border-white/10 relative overflow-hidden">
      {/* subtle starfield */}
      <div className="pointer-events-none absolute inset-0 opacity-30" style={{backgroundImage:
        "radial-gradient(2px 2px at 20% 30%, rgba(255,255,255,0.6) 50%, transparent 51%)," +
        "radial-gradient(1.5px 1.5px at 60% 70%, rgba(255,255,255,0.45) 50%, transparent 51%)," +
        "radial-gradient(1px 1px at 80% 20%, rgba(255,255,255,0.35) 50%, transparent 51%)," +
        "radial-gradient(1px 1px at 30% 80%, rgba(255,255,255,0.35) 50%, transparent 51%)"}} />
      <h2 className="text-3xl font-bold px-4 py-4 border-b border-white/10 tracking-tight relative">
        <span className="bg-gradient-to-r from-cyan-400 to-indigo-400 bg-clip-text text-transparent">Cosmic Sparks</span>
      </h2>
      <nav className="flex-1 px-0 py-3 relative text-lg">
        <Link href="/profile" className="flex items-center gap-4 h-14 w-full px-6 border-t border-b border-white/10 bg-white/5 hover:bg-white/10 transition text-left">
          <UserCircleIcon className="w-7 h-7 text-cyan-300" />
          <span className="font-semibold">Profile</span>
        </Link>
        <Link href="/map" className="flex items-center gap-4 h-14 w-full px-6 border-b border-white/10 hover:bg-white/10 transition text-left">
          <MapPinIcon className="w-7 h-7 text-indigo-300" />
          <span className="font-semibold">Map View</span>
        </Link>
        <Link href="/contact" className="flex items-center gap-4 h-14 w-full px-6 border-b border-white/10 hover:bg-white/10 transition text-left">
          <EnvelopeIcon className="w-7 h-7 text-purple-300" />
          <span className="font-semibold">Contact</span>
        </Link>
      </nav>
    </div>
    
  );
}
