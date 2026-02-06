import { useState, useRef, useEffect } from 'react';
import { Download, FileJson, Copy, CheckCircle } from 'lucide-react';
import { exportToJSON, copyToClipboard, generateStatsSummary } from '../../utils/exportHelpers';
import './ExportMenu.css';

const ExportMenu = ({ extractions, scriptTitle }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleExportJSON = () => {
    exportToJSON(extractions, scriptTitle);
    setIsOpen(false);
  };

  const handleCopyText = async () => {
    const success = await copyToClipboard(extractions);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
    setIsOpen(false);
  };

  const handleExportStats = () => {
    const stats = generateStatsSummary(extractions);
    exportToJSON(stats, `${scriptTitle}_stats`);
    setIsOpen(false);
  };

  return (
    <div className="export-menu" ref={menuRef}>
      <button 
        className="export-trigger"
        onClick={() => setIsOpen(!isOpen)}
      >
        <Download size={18} />
        Export
      </button>

      {isOpen && (
        <div className="export-dropdown">
          <button className="export-option" onClick={handleExportJSON}>
            <FileJson size={18} />
            <div className="option-content">
              <span className="option-title">Export as JSON</span>
              <span className="option-desc">Download all extractions</span>
            </div>
          </button>

          <button className="export-option" onClick={handleCopyText}>
            {copied ? <CheckCircle size={18} className="success-icon" /> : <Copy size={18} />}
            <div className="option-content">
              <span className="option-title">
                {copied ? 'Copied!' : 'Copy to Clipboard'}
              </span>
              <span className="option-desc">Copy extraction text</span>
            </div>
          </button>

          <button className="export-option" onClick={handleExportStats}>
            <Download size={18} />
            <div className="option-content">
              <span className="option-title">Export Stats</span>
              <span className="option-desc">Download summary statistics</span>
            </div>
          </button>
        </div>
      )}
    </div>
  );
};

export default ExportMenu;
