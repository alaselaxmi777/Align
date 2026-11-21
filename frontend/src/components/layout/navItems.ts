import {
  Compass,
  Users,
  Calendar,
  Target,
  Briefcase,
  MapPin,
  UserCheck,
  Sparkles,
  Globe,
  MessageSquare,
  Film,
  Award,
  FolderGit2,
  Bot,
  Lightbulb,
  Settings,
  House,
  LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  authOnly?: boolean;
  badge?: string;
}

export const PRIMARY_NAV_ITEMS: NavItem[] = [
  { to: "/discover", label: "Discover", icon: Compass },
  { to: "/communities", label: "Communities", icon: Users },
  { to: "/events", label: "Events", icon: Calendar },
  { to: "/goals/journey", label: "Goal Journey", icon: Target },
  { to: "/opportunities", label: "Opportunities", icon: Briefcase },
];

export const MORE_NAV_ITEMS: NavItem[] = [
  { to: "/places", label: "Places", icon: MapPin },
  { to: "/people", label: "People", icon: UserCheck },
  { to: "/circles", label: "Circles", icon: Sparkles },
  { to: "/map", label: "Discovery Map", icon: Globe },
  { to: "/feed", label: "Posts", icon: MessageSquare },
  { to: "/reels", label: "Reels", icon: Film },
  { to: "/projects", label: "Collaborate", icon: FolderGit2 },
  { to: "/achievements", label: "Achievements", icon: Award },
  { to: "/assistant", label: "AI Assistant", icon: Bot },
  { to: "/skills-hobbies", label: "Skills Catalog", icon: Lightbulb },
  { to: "/goals-interests", label: "Goals & Interests", icon: Compass },
  { to: "/settings", label: "Settings", icon: Settings },
];

export const MOBILE_PRIMARY_TABS: NavItem[] = [
  { to: "/discover", label: "Discover", icon: Compass },
  { to: "/communities", label: "Communities", icon: Users },
  { to: "/events", label: "Events", icon: Calendar },
];
