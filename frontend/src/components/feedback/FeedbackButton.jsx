import React, { useState, useRef } from 'react';
import { MessageSquare } from 'lucide-react';
import FeedbackDrawer from './FeedbackDrawer';
import './FeedbackButton.css';

const FeedbackButton = () => {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const buttonRef = useRef(null);

  const toggleDrawer = () => {
    setIsDrawerOpen(!isDrawerOpen);
  };

  return (
    <div className="feedback-button-container">
      <button 
        ref={buttonRef}
        className="feedback-button"
        onClick={toggleDrawer}
        title="Send Feedback"
      >
        <MessageSquare size={18} />
        <span>Feedback</span>
      </button>

      {isDrawerOpen && (
        <FeedbackDrawer 
          isOpen={isDrawerOpen}
          onClose={() => setIsDrawerOpen(false)}
          anchorRef={buttonRef}
        />
      )}
    </div>
  );
};

export default FeedbackButton;
