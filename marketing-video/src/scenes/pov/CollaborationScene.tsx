import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { MessageSquare, Users, Bell } from 'lucide-react';

export const CollaborationScene: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const avatarsAppear = interpolate(frame, [30, 50], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const comment1 = interpolate(frame, [60, 80], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const comment2 = interpolate(frame, [90, 110], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const notification = interpolate(frame, [120, 140], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#0f172a' }}>
      {/* Title */}
      <div
        style={{
          position: 'absolute',
          top: 80,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: titleOpacity,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
          <Users size={40} color="#fbbf24" />
          <h2
            style={{
              fontSize: 48,
              fontWeight: 700,
              color: '#f1f5f9',
              margin: 0,
            }}
          >
            Real-Time Collaboration
          </h2>
        </div>
        <p style={{ fontSize: 24, color: '#94a3b8', marginTop: 16 }}>
          Your entire team, in sync
        </p>
      </div>

      {/* Collaboration Interface */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 900,
          marginTop: 40,
        }}
      >
        {/* Team Members */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            gap: 16,
            marginBottom: 40,
            opacity: avatarsAppear,
          }}
        >
          {[
            { name: 'Director', color: '#fbbf24', initials: 'JD' },
            { name: 'Producer', color: '#10b981', initials: 'SM' },
            { name: 'AD', color: '#3b82f6', initials: 'KL' },
            { name: 'DP', color: '#a855f7', initials: 'RT' },
          ].map((member) => (
            <div key={member.name} style={{ textAlign: 'center' }}>
              <div
                style={{
                  width: 80,
                  height: 80,
                  borderRadius: '50%',
                  backgroundColor: member.color,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 28,
                  fontWeight: 700,
                  color: '#0f172a',
                  marginBottom: 8,
                  border: '4px solid #1e293b',
                }}
              >
                {member.initials}
              </div>
              <p style={{ fontSize: 14, color: '#94a3b8', margin: 0 }}>
                {member.name}
              </p>
            </div>
          ))}
        </div>

        {/* Comment Thread */}
        <div
          style={{
            backgroundColor: '#1e293b',
            borderRadius: 12,
            padding: 30,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
            <MessageSquare size={20} color="#fbbf24" />
            <h3 style={{ fontSize: 18, color: '#f1f5f9', margin: 0, fontWeight: 600 }}>
              Scene 2 Discussion
            </h3>
          </div>

          {/* Comment 1 */}
          <div
            style={{
              marginBottom: 20,
              opacity: comment1,
              transform: `translateY(${interpolate(frame, [60, 80], [20, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })}px)`,
            }}
          >
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: '50%',
                  backgroundColor: '#fbbf24',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 16,
                  fontWeight: 700,
                  color: '#0f172a',
                  flexShrink: 0,
                }}
              >
                JD
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={{ fontSize: 14, color: '#f1f5f9', fontWeight: 600 }}>
                    Director
                  </span>
                  <span style={{ fontSize: 12, color: '#64748b' }}>
                    2 min ago
                  </span>
                </div>
                <p
                  style={{
                    fontSize: 14,
                    color: '#cbd5e1',
                    margin: 0,
                    backgroundColor: '#0f172a',
                    padding: '12px 16px',
                    borderRadius: 8,
                  }}
                >
                  Let's add a tracking shot here. The briefcase is crucial for the plot.
                </p>
              </div>
            </div>
          </div>

          {/* Comment 2 */}
          <div
            style={{
              opacity: comment2,
              transform: `translateY(${interpolate(frame, [90, 110], [20, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })}px)`,
            }}
          >
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: '50%',
                  backgroundColor: '#a855f7',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 16,
                  fontWeight: 700,
                  color: '#0f172a',
                  flexShrink: 0,
                }}
              >
                RT
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={{ fontSize: 14, color: '#f1f5f9', fontWeight: 600 }}>
                    DP
                  </span>
                  <span style={{ fontSize: 12, color: '#64748b' }}>
                    Just now
                  </span>
                </div>
                <p
                  style={{
                    fontSize: 14,
                    color: '#cbd5e1',
                    margin: 0,
                    backgroundColor: '#0f172a',
                    padding: '12px 16px',
                    borderRadius: 8,
                  }}
                >
                  Perfect! I'll prep the Steadicam. Need golden hour lighting?
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Notification Badge */}
        {frame > 120 && (
          <div
            style={{
              position: 'absolute',
              top: -20,
              right: 20,
              backgroundColor: '#10b981',
              borderRadius: 20,
              padding: '8px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              opacity: notification,
              boxShadow: '0 4px 12px rgba(16, 185, 129, 0.4)',
            }}
          >
            <Bell size={16} color="#0f172a" />
            <span style={{ fontSize: 13, color: '#0f172a', fontWeight: 600 }}>
              3 new updates
            </span>
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
