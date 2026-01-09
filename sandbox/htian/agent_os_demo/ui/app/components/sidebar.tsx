"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { name: "Brain", href: "/" },
  { name: "Agents", href: "/agents" },
  { name: "Workflows", href: "/workflows" },
  { name: "Runs", href: "/runs" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r h-screen flex flex-col">
      <div className="p-4 font-semibold text-lg">
        Agent OS
        <div className="text-xs text-gray-500">Sandbox</div>
      </div>

      <nav className="flex-1 px-2 space-y-1">
        {navItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block px-3 py-2 rounded text-sm ${
                active
                  ? "bg-gray-600 font-medium text-white"
                  : "hover:bg-gray-600 hover:text-black text-white"
              }`}
            >
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t text-sm text-gray-600">
        👤 Howard
      </div>
    </aside>
  );
}
