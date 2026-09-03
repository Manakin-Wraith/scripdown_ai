// Mapbox Static Images preview. Renders an <img> when coords + a public token
// are all present; otherwise a placeholder keyed off geocodeStatus.
const TOKEN = import.meta.env.VITE_MAPBOX_PUBLIC_TOKEN;

export default function StaticMap({ lat, lng, geocodeStatus, height = 240 }) {
    const hasCoords = lat != null && lng != null && lat !== '' && lng !== '';

    if (!TOKEN) {
        return (
            <div className="static-map static-map--empty" style={{ height }}>
                Map preview unavailable
            </div>
        );
    }
    if (!hasCoords) {
        const msg = geocodeStatus === 'failed'
            ? "Address couldn't be located — add coordinates manually"
            : 'Add an address or coordinates to show a map';
        return (
            <div className="static-map static-map--empty" style={{ height }}>{msg}</div>
        );
    }

    const src = 'https://api.mapbox.com/styles/v1/mapbox/streets-v12/static/'
        + `pin-s+e11d48(${lng},${lat})/${lng},${lat},13/640x${Math.round(height)}@2x`
        + `?access_token=${TOKEN}`;
    return (
        <img
            className="static-map"
            src={src}
            alt="Location map"
            style={{ height, width: '100%', objectFit: 'cover' }}
        />
    );
}
