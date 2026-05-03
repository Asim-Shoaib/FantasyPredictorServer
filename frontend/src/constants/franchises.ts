export interface FranchiseConfig {
  name: string
  primary: string
  secondary: string
  textColor: string
  shortName: string
  emoji: string
  bgGradient: string
}

export const FRANCHISE_CONFIG: Record<string, FranchiseConfig> = {
  "Karachi Kings": {
    name: "Karachi Kings",
    primary: "#003F88",
    secondary: "#00AEEF",
    textColor: "#FFFFFF",
    shortName: "KK",
    emoji: "👑",
    bgGradient: "from-[#003F88] to-[#00AEEF]",
  },
  "Lahore Qalandars": {
    name: "Lahore Qalandars",
    primary: "#006633",
    secondary: "#00A651",
    textColor: "#FFFFFF",
    shortName: "LQ",
    emoji: "⚡",
    bgGradient: "from-[#006633] to-[#00A651]",
  },
  "Peshawar Zalmi": {
    name: "Peshawar Zalmi",
    primary: "#C8850A",
    secondary: "#F7941D",
    textColor: "#000000",
    shortName: "PZ",
    emoji: "🔥",
    bgGradient: "from-[#C8850A] to-[#F7941D]",
  },
  "Quetta Gladiators": {
    name: "Quetta Gladiators",
    primary: "#1A1A1A",
    secondary: "#C8A84B",
    textColor: "#FFFFFF",
    shortName: "QG",
    emoji: "⚔️",
    bgGradient: "from-[#1A1A1A] to-[#C8A84B]",
  },
  "Islamabad United": {
    name: "Islamabad United",
    primary: "#E31E26",
    secondary: "#003DA5",
    textColor: "#FFFFFF",
    shortName: "IU",
    emoji: "🦅",
    bgGradient: "from-[#E31E26] to-[#003DA5]",
  },
  "Multan Sultans": {
    name: "Multan Sultans",
    primary: "#5C1D8A",
    secondary: "#9B4FCA",
    textColor: "#FFFFFF",
    shortName: "MS",
    emoji: "👑",
    bgGradient: "from-[#5C1D8A] to-[#9B4FCA]",
  },
}

export const DEFAULT_FRANCHISE: FranchiseConfig = {
  name: "Unknown",
  primary: "#6366f1",
  secondary: "#818cf8",
  textColor: "#FFFFFF",
  shortName: "??",
  emoji: "🏏",
  bgGradient: "from-[#6366f1] to-[#818cf8]",
}

export function getFranchise(teamName: string): FranchiseConfig {
  return FRANCHISE_CONFIG[teamName] ?? DEFAULT_FRANCHISE
}
