import React, { useState, useRef, useEffect } from 'react';
import { X, Camera, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { submitFeedback } from '../../services/apiService';
import './FeedbackDrawer.css';

const FeedbackDrawer = ({ isOpen, onClose, anchorRef }) => {
  const { user } = useAuth();
  const drawerRef = useRef(null);
  
  // Form state
  const [category, setCategory] = useState('bug');
  const [priority, setPriority] = useState('medium');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [screenshot, setScreenshot] = useState(null);
  const [screenshotPreview, setScreenshotPreview] = useState(null);
  
  // UI state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [charCount, setCharCount] = useState(0);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (drawerRef.current && !drawerRef.current.contains(event.target) && 
          anchorRef?.current && !anchorRef.current.contains(event.target)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen, onClose, anchorRef]);

  // Reset form when opened
  useEffect(() => {
    if (isOpen) {
      setCategory('bug');
      setPriority('medium');
      setSubject('');
      setDescription('');
      setScreenshot(null);
      setScreenshotPreview(null);
      setError(null);
      setSuccess(false);
      setCharCount(0);
    }
  }, [isOpen]);

  // Handle screenshot upload
  const handleScreenshotChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      setError('Please upload a PNG, JPG, or WebP image');
      return;
    }

    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      setError('Screenshot must be less than 5MB');
      return;
    }

    setScreenshot(file);
    setError(null);

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setScreenshotPreview(reader.result);
    };
    reader.readAsDataURL(file);
  };

  // Remove screenshot
  const removeScreenshot = () => {
    setScreenshot(null);
    setScreenshotPreview(null);
  };

  // Capture page context
  const capturePageContext = () => {
    return {
      url: window.location.href,
      route: window.location.pathname,
      user_agent: navigator.userAgent,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      },
      timestamp: new Date().toISOString()
    };
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!subject.trim()) {
      setError('Subject is required');
      return;
    }
    if (subject.length > 200) {
      setError('Subject must be 200 characters or less');
      return;
    }
    if (!description.trim()) {
      setError('Description is required');
      return;
    }
    if (description.length > 2000) {
      setError('Description must be 2000 characters or less');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      // Prepare form data
      const formData = new FormData();
      formData.append('category', category);
      formData.append('priority', priority);
      formData.append('subject', subject.trim());
      formData.append('description', description.trim());
      formData.append('page_context', JSON.stringify(capturePageContext()));
      
      if (screenshot) {
        formData.append('screenshot', screenshot);
      }

      // Submit feedback
      await submitFeedback(formData);

      // Show success
      setSuccess(true);
      
      // Close after 2 seconds
      setTimeout(() => {
        onClose();
      }, 2000);

    } catch (err) {
      console.error('Error submitting feedback:', err);
      
      if (err.response?.status === 429) {
        setError('Rate limit exceeded. Maximum 5 feedback submissions per day.');
      } else if (err.response?.data?.error) {
        setError(err.response.data.error);
      } else {
        setError('Failed to submit feedback. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle description change with character count
  const handleDescriptionChange = (e) => {
    const value = e.target.value;
    setDescription(value);
    setCharCount(value.length);
  };

  if (!isOpen) return null;

  // Success state
  if (success) {
    return (
      <div className="feedback-drawer" ref={drawerRef}>
        <div className="feedback-success">
          <CheckCircle size={48} className="success-icon" />
          <h3>Feedback Submitted!</h3>
          <p>Thank you for helping us improve. We'll review your feedback shortly.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="feedback-drawer" ref={drawerRef}>
      <div className="feedback-header">
        <h3>Send Feedback</h3>
        <button className="close-btn" onClick={onClose} disabled={isSubmitting}>
          <X size={20} />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="feedback-form">
        {/* Category Selection */}
        <div className="form-group">
          <label>Category *</label>
          <div className="category-pills">
            <button
              type="button"
              className={`category-pill ${category === 'bug' ? 'active' : ''}`}
              onClick={() => setCategory('bug')}
              disabled={isSubmitting}
            >
              🐛 Bug Report
            </button>
            <button
              type="button"
              className={`category-pill ${category === 'feature' ? 'active' : ''}`}
              onClick={() => setCategory('feature')}
              disabled={isSubmitting}
            >
              ✨ Feature Request
            </button>
            <button
              type="button"
              className={`category-pill ${category === 'ui_ux' ? 'active' : ''}`}
              onClick={() => setCategory('ui_ux')}
              disabled={isSubmitting}
            >
              🎨 UI/UX Issue
            </button>
            <button
              type="button"
              className={`category-pill ${category === 'general' ? 'active' : ''}`}
              onClick={() => setCategory('general')}
              disabled={isSubmitting}
            >
              💬 General
            </button>
          </div>
        </div>

        {/* Priority Selection */}
        <div className="form-group">
          <label>Priority</label>
          <select 
            value={priority} 
            onChange={(e) => setPriority(e.target.value)}
            disabled={isSubmitting}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>

        {/* Subject */}
        <div className="form-group">
          <label>Subject * <span className="char-limit">{subject.length}/200</span></label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Brief summary of your feedback"
            maxLength={200}
            disabled={isSubmitting}
            required
          />
        </div>

        {/* Description */}
        <div className="form-group">
          <label>Description * <span className="char-limit">{charCount}/2000</span></label>
          <textarea
            value={description}
            onChange={handleDescriptionChange}
            placeholder="Provide detailed information about your feedback..."
            maxLength={2000}
            rows={6}
            disabled={isSubmitting}
            required
          />
        </div>

        {/* Screenshot Upload */}
        <div className="form-group">
          <label>Screenshot (optional)</label>
          {!screenshotPreview ? (
            <label className="screenshot-upload">
              <input
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/webp"
                onChange={handleScreenshotChange}
                disabled={isSubmitting}
                style={{ display: 'none' }}
              />
              <Camera size={24} />
              <span>Click to upload screenshot</span>
              <small>PNG, JPG, or WebP (max 5MB)</small>
            </label>
          ) : (
            <div className="screenshot-preview">
              <img src={screenshotPreview} alt="Screenshot preview" />
              <button
                type="button"
                className="remove-screenshot"
                onClick={removeScreenshot}
                disabled={isSubmitting}
              >
                <X size={16} />
              </button>
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Submit Button */}
        <button 
          type="submit" 
          className="submit-btn"
          disabled={isSubmitting || !subject.trim() || !description.trim()}
        >
          {isSubmitting ? (
            <>
              <Loader size={16} className="spin" />
              <span>Submitting...</span>
            </>
          ) : (
            <span>Submit Feedback</span>
          )}
        </button>
      </form>
    </div>
  );
};

export default FeedbackDrawer;
