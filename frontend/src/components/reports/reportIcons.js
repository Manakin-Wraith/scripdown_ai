import {
    FileText, Users, MapPin, Package, Shirt, Film, List, BookOpen,
    UserPlus, Zap, Flame, Sparkles, Car, PawPrint,
} from 'lucide-react';

export const REPORT_ICONS = {
    scene_breakdown: Film,
    day_out_of_days: Users,
    location: MapPin,
    props: Package,
    wardrobe: Shirt,
    one_liner: List,
    full_breakdown: BookOpen,
    extras: UserPlus,
    sfx: Zap,
    special_effects: Zap,
    stunts: Flame,
    makeup: Sparkles,
    vehicles: Car,
    animals: PawPrint,
};

export const reportIcon = (type) => REPORT_ICONS[type] || FileText;
