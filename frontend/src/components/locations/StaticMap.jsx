// Mapbox Static Images preview. Renders an <img> when coords + a public token
// are all present; otherwise a placeholder keyed off geocodeStatus.
const TOKEN = import.meta.env.VITE_MAPBOX_PUBLIC_TOKEN;

export default function StaticMap({ lat, lng, geocodeStatus, height = 240 }) {
    const nLat = lat === '' || lat == null ? null : Number(lat);
    const nLng = lng === '' || lng == null ? null : Number(lng);
    const hasCoords = nLat != null && nLng != null;
    const validCoords = hasCoords
        && Number.isFinite(nLat) && Math.abs(nLat) <= 90
        && Number.isFinite(nLng) && Math.abs(nLng) <= 180;

    if (!TOKEN) {
        return (
            <div className="static-map static-map--empty" style={{ height }}>
                Map preview unavailable
            </div>
        );
    }
    if (!validCoords) {
        let msg = 'No coordinates yet — add an address or lat/lng to show a map';
        if (hasCoords) {
            msg = 'Coordinates out of range — latitude −90 to 90, longitude −180 to 180';
        } else if (geocodeStatus === 'failed') {
            msg = "Address couldn't be located — add coordinates manually";
        }
        return (
            <div className="static-map static-map--empty" style={{ height }}>{msg}</div>
        );
    }

    const src = 'https://api.mapbox.com/styles/v1/mapbox/streets-v12/static/'
        + `pin-s+e11d48(${nLng},${nLat})/${nLng},${nLat},13/640x${Math.round(height)}@2x`
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
