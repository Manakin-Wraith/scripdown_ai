/**
 * Shared extraction class configuration.
 * Single source of truth for langextract class metadata:
 * labels, icons, colors, and category-to-department mappings.
 *
 * Used by: ExtractionViewer, FilterPanel, ExtractionStats,
 *          SceneDetail, ReportBuilder, and any future consumers.
 */
import {
  Film,
  Users,
  MessageSquare,
  Sparkles,
  Shirt,
  MapPin,
  Heart,
  Link,
  Zap,
  Car,
  Music,
  Clock,
  Palette,
  Package,
  Volume2,
  Dog,
  UserPlus,
  Flame,
  Building2,
  FileText,
  Home,
  Activity,
  Camera
} from 'lucide-react';

// ============================================
// Extraction Class Metadata
// Maps langextract extraction_class values to
// display label, icon component, and theme color.
// ============================================
export const CLASS_METADATA = {
  'scene_header':   { label: 'Scene Headers',    icon: Film,           color: '#6366f1' },
  'character':      { label: 'Characters',        icon: Users,          color: '#3b82f6' },
  'dialogue':       { label: 'Dialogue',          icon: MessageSquare,  color: '#14b8a6' },
  'action':         { label: 'Action',            icon: Activity,       color: '#dc2626' },
  'prop':           { label: 'Props',             icon: Package,        color: '#06b6d4' },
  'wardrobe':       { label: 'Wardrobe',          icon: Shirt,          color: '#8b5cf6' },
  'location_detail':{ label: 'Location Details',  icon: MapPin,         color: '#10b981' },
  'emotion':        { label: 'Emotions',          icon: Heart,          color: '#db2777' },
  'relationship':   { label: 'Relationships',     icon: Link,           color: '#ec4899' },
  'special_fx':     { label: 'Special FX',        icon: Zap,            color: '#eab308' },
  'vehicle':        { label: 'Vehicles',          icon: Car,            color: '#ef4444' },
  'sound':          { label: 'Sound',             icon: Volume2,        color: '#a855f7' },
  'transition':     { label: 'Transitions',       icon: Clock,          color: '#f59e0b' },
  'makeup_hair':    { label: 'Makeup & Hair',     icon: Palette,        color: '#f97316' }
};

// ============================================
// Scene Detail Category Config
// Maps breakdown categories displayed in SceneDetail
// to their icon, label, scene data key, and tag CSS class.
// ============================================
export const SCENE_CATEGORIES = {
  characters:   { label: 'Characters',    icon: Users,     color: '#3b82f6', tagClass: 'character-tag' },
  props:        { label: 'Props',         icon: Package,   color: '#06b6d4', tagClass: 'prop-tag' },
  wardrobe:     { label: 'Wardrobe',      icon: Shirt,     color: '#8b5cf6', tagClass: 'wardrobe-tag' },
  makeup_hair:  { label: 'Makeup & Hair', icon: Palette,   color: '#f97316', tagClass: 'makeup-tag' },
  special_fx:   { label: 'Special FX',    icon: Sparkles,  color: '#eab308', tagClass: 'fx-tag' },
  vehicles:     { label: 'Vehicles',      icon: Car,       color: '#ef4444', tagClass: 'vehicle-tag' },
  locations:    { label: 'Locations',     icon: Building2, color: '#10b981', tagClass: 'location-tag' },
  sound:        { label: 'Sound',         icon: Volume2,   color: '#a855f7', tagClass: 'sound-tag' },
  animals:      { label: 'Animals',       icon: Dog,       color: '#78716c', tagClass: 'animal-tag' },
  extras:       { label: 'Extras',        icon: UserPlus,  color: '#64748b', tagClass: 'extra-tag' },
  stunts:       { label: 'Stunts',        icon: Flame,     color: '#b91c1c', tagClass: 'stunt-tag' }
};

// ============================================
// Category → Department Mapping
// Used for note counting in SceneDetail.
// ============================================
export const CATEGORY_DEPARTMENTS = {
  characters:   ['director', 'casting', 'actor'],
  props:        ['production_design', 'director'],
  wardrobe:     ['costume', 'director'],
  makeup_hair:  ['makeup_hair', 'director'],
  special_fx:   ['vfx', 'director'],
  vehicles:     ['locations', 'director', 'production_design'],
  locations:    ['locations', 'production_design', 'director'],
  sound:        ['sound', 'director', 'post_production'],
  animals:      ['production_design', 'director'],
  extras:       ['casting', 'director'],
  stunts:       ['stunts', 'director', 'safety']
};

// ============================================
// Metric Card Config for ExtractionStats
// ============================================
export const METRIC_CARDS = [
  { key: 'pages',      label: 'Total Pages',  icon: FileText },
  { key: 'eighths',    label: 'Total Eighths', icon: Clock },
  { key: 'characters', label: 'Characters',    icon: Users },
  { key: 'locations',  label: 'Locations',     icon: MapPin },
  { key: 'int-ext',    label: 'INT / EXT',     icon: Home },
  { key: 'props',      label: 'Props',         icon: Package },
  { key: 'vehicles',   label: 'Vehicles',      icon: Car },
  { key: 'special-fx', label: 'Special FX',    icon: Sparkles }
];

// ============================================
// Extraction class → Scene breakdown category mapping
// Maps langextract extraction_class names to the
// SceneDetail category keys for unified display.
// ============================================
export const EXTRACTION_TO_SCENE_CATEGORY = {
  'character':       'characters',
  'prop':            'props',
  'wardrobe':        'wardrobe',
  'makeup_hair':     'makeup_hair',
  'special_fx':      'special_fx',
  'vehicle':         'vehicles',
  'location_detail': 'locations',
  'sound':           'sound',
  'dialogue':        null,       // displayed separately
  'action':          null,       // displayed separately
  'scene_header':    null,       // scene-level metadata
  'emotion':         null,       // enrichment data
  'relationship':    null,       // enrichment data
  'transition':      null        // enrichment data
};

/**
 * Get metadata for a given extraction class, with a safe fallback.
 * @param {string} className - The extraction_class value
 * @returns {{ label: string, icon: import('lucide-react').LucideIcon, color: string }}
 */
export const getClassMetadata = (className) => {
  return CLASS_METADATA[className] || { label: className, icon: Sparkles, color: '#6b7280' };
};
