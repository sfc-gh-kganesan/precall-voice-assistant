interface SnowflakeLogoProps {
  className?: string
  size?: number
}

export function SnowflakeLogo({ className = '', size = 32 }: SnowflakeLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 256 256"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <path
        d="M128 28L147.5 78.5L173.5 47.5L166 98L210 85L188 128L210 171L166 158L173.5 208.5L147.5 177.5L128 228L108.5 177.5L82.5 208.5L90 158L46 171L68 128L46 85L90 98L82.5 47.5L108.5 78.5L128 28Z"
        fill="currentColor"
        className="text-primary"
      />
    </svg>
  )
}
