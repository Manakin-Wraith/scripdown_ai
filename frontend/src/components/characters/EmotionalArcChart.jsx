import React, { useState, useRef, useMemo, useCallback } from 'react';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import './EmotionalArcChart.css';

/**
 * EmotionalArcChart - Scalable visualization for character emotional arcs
 * 
 * Features:
 * - SVG line chart with smooth curves
 * - Heatmap timeline strip
 * - Zoom in/out capability
 * - Interactive hover tooltips
 * - Handles 100+ scenes gracefully
 */
const EmotionalArcChart = ({ sceneBreakdown }) => {
    const chartRef = useRef(null);
    const [zoomLevel, setZoomLevel] = useState(1);
    const [panOffset, setPanOffset] = useState(0);
    const [hoveredPoint, setHoveredPoint] = useState(null);
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState(0);

    // Process and sort scene data
    const chartData = useMemo(() => {
        if (!sceneBreakdown) return [];
        
        return Object.entries(sceneBreakdown)
            .map(([sceneNum, data]) => {
                const parsedNum = parseInt(sceneNum, 10);
                return {
                    sceneNumber: isNaN(parsedNum) ? 0 : parsedNum,
                    sceneLabel: sceneNum, // Keep original for display
                    emotion: data.emotion || 'Neutral',
                    intensity: Math.min(10, Math.max(1, data.intensity || 5)),
                };
            })
            .filter(d => d.sceneNumber > 0) // Filter out invalid scene numbers
            .sort((a, b) => a.sceneNumber - b.sceneNumber);
    }, [sceneBreakdown]);

    // Chart dimensions
    const CHART_HEIGHT = 180;
    const HEATMAP_HEIGHT = 24;
    const PADDING = { top: 20, right: 20, bottom: 40, left: 40 };
    
    // Calculate visible width based on zoom
    const baseWidth = Math.max(600, chartData.length * 30);
    const visibleWidth = baseWidth * zoomLevel;
    
    // Generate SVG path for the line chart
    const linePath = useMemo(() => {
        if (chartData.length === 0) return '';
        
        const xScale = (visibleWidth - PADDING.left - PADDING.right) / Math.max(1, chartData.length - 1);
        const yScale = (CHART_HEIGHT - PADDING.top - PADDING.bottom) / 10;
        
        // Create smooth curve using cardinal spline
        const points = chartData.map((d, i) => ({
            x: PADDING.left + i * xScale,
            y: CHART_HEIGHT - PADDING.bottom - (d.intensity * yScale),
        }));
        
        if (points.length === 1) {
            return `M ${points[0].x} ${points[0].y}`;
        }
        
        // Generate smooth curve
        let path = `M ${points[0].x} ${points[0].y}`;
        
        for (let i = 0; i < points.length - 1; i++) {
            const p0 = points[Math.max(0, i - 1)];
            const p1 = points[i];
            const p2 = points[i + 1];
            const p3 = points[Math.min(points.length - 1, i + 2)];
            
            // Catmull-Rom to Bezier conversion
            const cp1x = p1.x + (p2.x - p0.x) / 6;
            const cp1y = p1.y + (p2.y - p0.y) / 6;
            const cp2x = p2.x - (p3.x - p1.x) / 6;
            const cp2y = p2.y - (p3.y - p1.y) / 6;
            
            path += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
        }
        
        return path;
    }, [chartData, visibleWidth]);

    // Generate area fill path
    const areaPath = useMemo(() => {
        if (!linePath || chartData.length === 0) return '';
        
        const xScale = (visibleWidth - PADDING.left - PADDING.right) / Math.max(1, chartData.length - 1);
        const lastX = PADDING.left + (chartData.length - 1) * xScale;
        const baseline = CHART_HEIGHT - PADDING.bottom;
        
        return `${linePath} L ${lastX} ${baseline} L ${PADDING.left} ${baseline} Z`;
    }, [linePath, chartData, visibleWidth]);

    // Get color based on intensity
    const getIntensityColor = (intensity) => {
        if (intensity <= 3) return '#10b981'; // Green - Low
        if (intensity <= 6) return '#f59e0b'; // Yellow - Medium
        if (intensity <= 8) return '#f97316'; // Orange - High
        return '#ef4444'; // Red - Extreme
    };

    // Calculate point positions for hover detection
    const pointPositions = useMemo(() => {
        const xScale = (visibleWidth - PADDING.left - PADDING.right) / Math.max(1, chartData.length - 1);
        const yScale = (CHART_HEIGHT - PADDING.top - PADDING.bottom) / 10;
        
        return chartData.map((d, i) => ({
            ...d,
            x: PADDING.left + i * xScale,
            y: CHART_HEIGHT - PADDING.bottom - (d.intensity * yScale),
            index: i,
        }));
    }, [chartData, visibleWidth]);

    // Handle mouse move for hover
    const handleMouseMove = useCallback((e) => {
        if (isDragging) {
            const delta = e.clientX - dragStart;
            setPanOffset(prev => Math.max(0, Math.min(visibleWidth - 600, prev - delta)));
            setDragStart(e.clientX);
            return;
        }

        const rect = chartRef.current?.getBoundingClientRect();
        if (!rect) return;
        
        const mouseX = e.clientX - rect.left + panOffset;
        
        // Find closest point
        let closest = null;
        let minDist = Infinity;
        
        pointPositions.forEach(point => {
            const dist = Math.abs(point.x - mouseX);
            if (dist < minDist && dist < 30) {
                minDist = dist;
                closest = point;
            }
        });
        
        setHoveredPoint(closest);
    }, [pointPositions, panOffset, isDragging, dragStart, visibleWidth]);

    const handleMouseDown = (e) => {
        if (zoomLevel > 1) {
            setIsDragging(true);
            setDragStart(e.clientX);
        }
    };

    const handleMouseUp = () => {
        setIsDragging(false);
    };

    const handleMouseLeave = () => {
        setHoveredPoint(null);
        setIsDragging(false);
    };

    // Zoom controls
    const handleZoomIn = () => setZoomLevel(prev => Math.min(3, prev + 0.5));
    const handleZoomOut = () => {
        setZoomLevel(prev => Math.max(1, prev - 0.5));
        setPanOffset(0);
    };
    const handleReset = () => {
        setZoomLevel(1);
        setPanOffset(0);
    };

    // Calculate adaptive label interval
    const labelInterval = useMemo(() => {
        const visibleScenes = chartData.length / zoomLevel;
        if (visibleScenes <= 10) return 1;
        if (visibleScenes <= 20) return 2;
        if (visibleScenes <= 50) return 5;
        if (visibleScenes <= 100) return 10;
        return 20;
    }, [chartData.length, zoomLevel]);

    if (chartData.length === 0) {
        return (
            <div className="emotional-arc-empty">
                <p>No emotional data available</p>
            </div>
        );
    }

    return (
        <div className="emotional-arc-chart">
            {/* Zoom Controls */}
            <div className="arc-controls">
                <button 
                    className="arc-control-btn" 
                    onClick={handleZoomIn}
                    disabled={zoomLevel >= 3}
                    title="Zoom In"
                >
                    <ZoomIn size={16} />
                </button>
                <span className="zoom-level">{Math.round(zoomLevel * 100)}%</span>
                <button 
                    className="arc-control-btn" 
                    onClick={handleZoomOut}
                    disabled={zoomLevel <= 1}
                    title="Zoom Out"
                >
                    <ZoomOut size={16} />
                </button>
                <button 
                    className="arc-control-btn" 
                    onClick={handleReset}
                    title="Reset View"
                >
                    <Maximize2 size={16} />
                </button>
            </div>

            {/* Main Chart Area */}
            <div 
                className="arc-chart-wrapper"
                ref={chartRef}
                onMouseMove={handleMouseMove}
                onMouseDown={handleMouseDown}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseLeave}
                style={{ cursor: isDragging ? 'grabbing' : (zoomLevel > 1 ? 'grab' : 'crosshair') }}
            >
                {/* Y-Axis Labels */}
                <div className="arc-y-axis">
                    <span>10</span>
                    <span>5</span>
                    <span>0</span>
                </div>

                {/* Chart Container */}
                <div className="arc-chart-container">
                    <svg 
                        width={visibleWidth} 
                        height={CHART_HEIGHT + HEATMAP_HEIGHT + 20}
                        style={{ transform: `translateX(-${panOffset}px)` }}
                    >
                        {/* Background intensity zones */}
                        <defs>
                            <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="var(--primary-500)" stopOpacity="0.3" />
                                <stop offset="100%" stopColor="var(--primary-500)" stopOpacity="0.05" />
                            </linearGradient>
                        </defs>

                        {/* Grid lines */}
                        {[0, 2.5, 5, 7.5, 10].map((val, i) => {
                            const yScale = (CHART_HEIGHT - PADDING.top - PADDING.bottom) / 10;
                            const y = CHART_HEIGHT - PADDING.bottom - (val * yScale);
                            return (
                                <line
                                    key={i}
                                    x1={PADDING.left}
                                    y1={y}
                                    x2={visibleWidth - PADDING.right}
                                    y2={y}
                                    stroke="var(--gray-200)"
                                    strokeDasharray={val === 5 ? "none" : "4,4"}
                                    strokeWidth={val === 5 ? 1.5 : 1}
                                />
                            );
                        })}

                        {/* Area fill */}
                        <path
                            d={areaPath}
                            fill="url(#areaGradient)"
                        />

                        {/* Main line */}
                        <path
                            d={linePath}
                            fill="none"
                            stroke="var(--primary-500)"
                            strokeWidth={2.5}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        />

                        {/* Data points */}
                        {pointPositions.map((point, i) => (
                            <circle
                                key={i}
                                cx={point.x}
                                cy={point.y}
                                r={hoveredPoint?.index === i ? 6 : 4}
                                fill={getIntensityColor(point.intensity)}
                                stroke="white"
                                strokeWidth={2}
                                style={{ transition: 'r 0.15s ease' }}
                            />
                        ))}

                        {/* X-axis labels */}
                        {chartData.map((d, i) => {
                            if (i % labelInterval !== 0) return null;
                            const xScale = (visibleWidth - PADDING.left - PADDING.right) / Math.max(1, chartData.length - 1);
                            const x = PADDING.left + i * xScale;
                            return (
                                <text
                                    key={i}
                                    x={x}
                                    y={CHART_HEIGHT - 8}
                                    textAnchor="middle"
                                    className="arc-x-label"
                                >
                                    {d.sceneNumber}
                                </text>
                            );
                        })}

                        {/* Heatmap strip */}
                        <g transform={`translate(0, ${CHART_HEIGHT + 5})`}>
                            {chartData.map((d, i) => {
                                const xScale = (visibleWidth - PADDING.left - PADDING.right) / chartData.length;
                                const x = PADDING.left + i * xScale;
                                return (
                                    <rect
                                        key={i}
                                        x={x}
                                        y={0}
                                        width={Math.max(2, xScale - 1)}
                                        height={HEATMAP_HEIGHT}
                                        fill={getIntensityColor(d.intensity)}
                                        rx={2}
                                        opacity={hoveredPoint?.index === i ? 1 : 0.8}
                                    />
                                );
                            })}
                        </g>

                        {/* Hover indicator line */}
                        {hoveredPoint && (
                            <line
                                x1={hoveredPoint.x}
                                y1={PADDING.top}
                                x2={hoveredPoint.x}
                                y2={CHART_HEIGHT + HEATMAP_HEIGHT + 5}
                                stroke="var(--primary-600)"
                                strokeWidth={1}
                                strokeDasharray="4,4"
                                opacity={0.7}
                            />
                        )}
                    </svg>

                    {/* Tooltip - Smart positioning: below point when near top, above when near bottom */}
                    {hoveredPoint && (() => {
                        const tooltipHeight = 90;
                        const isNearTop = hoveredPoint.y < tooltipHeight + 20;
                        const tooltipTop = isNearTop 
                            ? hoveredPoint.y + 20  // Position below the point
                            : hoveredPoint.y - tooltipHeight - 10; // Position above the point
                        
                        return (
                            <div 
                                className={`arc-tooltip ${isNearTop ? 'tooltip-below' : 'tooltip-above'}`}
                                style={{
                                    left: Math.max(80, Math.min(hoveredPoint.x - panOffset, chartRef.current?.offsetWidth - 80 || 500)),
                                    top: tooltipTop,
                                }}
                            >
                                <div className="tooltip-scene">Scene {hoveredPoint.sceneNumber}</div>
                                <div className="tooltip-emotion">{hoveredPoint.emotion}</div>
                                <div className="tooltip-intensity">
                                    <span style={{ color: getIntensityColor(hoveredPoint.intensity) }}>
                                        {hoveredPoint.intensity}/10
                                    </span>
                                    <div className="tooltip-intensity-bar">
                                        <div 
                                            className="tooltip-intensity-fill"
                                            style={{ 
                                                width: `${hoveredPoint.intensity * 10}%`,
                                                background: getIntensityColor(hoveredPoint.intensity)
                                            }}
                                        />
                                    </div>
                                </div>
                            </div>
                        );
                    })()}
                </div>
            </div>

            {/* Chart Info Row */}
            <div className="arc-info-row">
                <div className="arc-axis-label">
                    <span className="axis-label-text">Intensity Scale (1-10)</span>
                </div>
                <div className="arc-heatmap-label">
                    <span className="heatmap-label-text">Timeline Overview</span>
                </div>
            </div>

            {/* Legend */}
            <div className="arc-legend">
                <div className="legend-item">
                    <span className="legend-dot" style={{ background: '#10b981' }}></span>
                    <span>Low (1-3)</span>
                </div>
                <div className="legend-item">
                    <span className="legend-dot" style={{ background: '#f59e0b' }}></span>
                    <span>Medium (4-6)</span>
                </div>
                <div className="legend-item">
                    <span className="legend-dot" style={{ background: '#f97316' }}></span>
                    <span>High (7-8)</span>
                </div>
                <div className="legend-item">
                    <span className="legend-dot" style={{ background: '#ef4444' }}></span>
                    <span>Extreme (9-10)</span>
                </div>
                <div className="legend-divider"></div>
                <div className="legend-stat">
                    <span className="stat-value">{chartData.length}</span>
                    <span className="stat-label">Scenes</span>
                </div>
            </div>

            {/* Mini-map for navigation when zoomed */}
            {zoomLevel > 1 && (
                <div className="arc-minimap">
                    <div 
                        className="minimap-viewport"
                        style={{
                            width: `${100 / zoomLevel}%`,
                            left: `${(panOffset / visibleWidth) * 100}%`,
                        }}
                    />
                </div>
            )}
        </div>
    );
};

export default EmotionalArcChart;
