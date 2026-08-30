"use client";

import { useId, useState } from "react";

/** Small (i) affordance that reveals an explanatory tooltip on hover or keyboard focus. */
export function InfoTooltip({ text }: { text: string }) {
  const [visible, setVisible] = useState(false);
  const id = useId();

  return (
    <span className="relative inline-flex">
      <button
        type="button"
        aria-describedby={id}
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full text-[10px] leading-none font-semibold text-zinc-500 bg-zinc-200 hover:bg-zinc-300 dark:text-zinc-400 dark:bg-zinc-700 dark:hover:bg-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-400"
      >
        i<span className="sr-only"> — more info</span>
      </button>
      <span
        id={id}
        role="tooltip"
        className={`absolute z-20 bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-[220px] rounded-lg bg-zinc-900 dark:bg-zinc-700 px-2.5 py-1.5 text-xs font-normal normal-case text-white shadow-lg pointer-events-none transition-opacity ${
          visible ? "opacity-100" : "opacity-0"
        }`}
      >
        {text}
        <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-zinc-900 dark:border-t-zinc-700" />
      </span>
    </span>
  );
}
