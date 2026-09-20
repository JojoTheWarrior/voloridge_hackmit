interface CastleLogoProps {
  size?: number
  className?: string
}

export function CastleLogo({ size = 16, className }: CastleLogoProps) {
  return (
    <svg
      role="img"
      aria-label="kingdom"
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="currentColor"
      className={className}
    >
      <path d="M1 2h3v2h2V2h4v2h2V2h3v13h-5v-4a2 2 0 0 0-4 0v4H1z" />
    </svg>
  )
}
