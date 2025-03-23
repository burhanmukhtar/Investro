import React, { useState, useEffect } from 'react';
import { Bell, ArrowRight, X, Award, Zap, BarChart3, Rocket } from 'lucide-react';

const AnnouncementBanner = () => {
  const [currentAnnouncement, setCurrentAnnouncement] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);
  const [dismissed, setDismissed] = useState([]);

  // Example announcements with different priorities and types
  const announcements = [
    {
      id: 1,
      title: "New Trading Features Released",
      content: "We've upgraded our platform with advanced charting tools, automated trading bots, and reduced fees for all premium users.",
      type: "feature",
      priority: "high",
      icon: <Rocket className="text-indigo-500" />,
      bgClass: "bg-indigo-50 border-indigo-200",
      action: "Explore Now"
    },
    {
      id: 2,
      title: "Flash Sale: 50% Off Trading Fees",
      content: "For the next 24 hours, enjoy half price trading fees on all currency pairs. Limited time offer!",
      type: "promotion",
      priority: "urgent",
      icon: <Zap className="text-amber-500" />,
      bgClass: "bg-amber-50 border-amber-200",
      action: "Claim Offer",
      countdown: true
    },
    {
      id: 3,
      title: "Security Update Required",
      content: "Please update your account security settings to enable our new two-factor authentication system.",
      type: "security",
      priority: "critical",
      icon: <Bell className="text-rose-500" />,
      bgClass: "bg-rose-50 border-rose-200",
      action: "Update Now"
    },
    {
      id: 4,
      title: "Bitcoin Halving Event Analysis",
      content: "Join our expert panel discussing the upcoming Bitcoin halving and potential market impacts.",
      type: "event",
      priority: "medium",
      icon: <BarChart3 className="text-emerald-500" />,
      bgClass: "bg-emerald-50 border-emerald-200",
      action: "Register"
    }
  ].filter(announcement => !dismissed.includes(announcement.id));

  // Rotate through announcements
  useEffect(() => {
    if (announcements.length === 0) return;
    
    const interval = setInterval(() => {
      if (!isExpanded) {
        setCurrentAnnouncement((prev) => (prev + 1) % announcements.length);
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [currentAnnouncement, announcements.length, isExpanded]);

  // Countdown timer for urgent announcements
  const [timeLeft, setTimeLeft] = useState("23:59:59");
  
  useEffect(() => {
    const countdownInterval = setInterval(() => {
      const [hours, minutes, seconds] = timeLeft.split(':').map(Number);
      let newSeconds = seconds - 1;
      let newMinutes = minutes;
      let newHours = hours;
      
      if (newSeconds < 0) {
        newSeconds = 59;
        newMinutes -= 1;
      }
      
      if (newMinutes < 0) {
        newMinutes = 59;
        newHours -= 1;
      }
      
      if (newHours < 0) {
        newHours = 23;
      }
      
      setTimeLeft(`${String(newHours).padStart(2, '0')}:${String(newMinutes).padStart(2, '0')}:${String(newSeconds).padStart(2, '0')}`);
    }, 1000);
    
    return () => clearInterval(countdownInterval);
  }, [timeLeft]);

  if (announcements.length === 0) return null;

  const announcement = announcements[currentAnnouncement];

  return (
    <div className="w-full max-w-5xl mx-auto">
      <div className={`relative rounded-lg shadow-sm border overflow-hidden transition-all duration-300 ${announcement.bgClass} ${isExpanded ? 'p-6' : 'py-3 px-4'}`}>
        {/* Announcement Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 flex-1">
            <div className="flex-shrink-0">
              {announcement.icon}
            </div>
            <div className="flex-1">
              <h3 className="font-bold text-gray-900 flex items-center">
                {announcement.title}
                {announcement.priority === "urgent" && (
                  <span className="ml-2 text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded-full animate-pulse">Urgent</span>
                )}
              </h3>
              {!isExpanded && (
                <p className="text-sm text-gray-700 line-clamp-1">{announcement.content}</p>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-2 ml-2">
            {announcement.countdown && (
              <div className="text-xs font-mono bg-white bg-opacity-80 px-2 py-1 rounded text-red-600 font-semibold">
                {timeLeft}
              </div>
            )}
            <button 
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-gray-500 hover:text-gray-700 flex-shrink-0"
            >
              <span className="sr-only">{isExpanded ? 'Collapse' : 'Expand'}</span>
              {isExpanded ? <X size={16} /> : <ArrowRight size={16} />}
            </button>
            <button 
              onClick={() => setDismissed([...dismissed, announcement.id])}
              className="text-gray-500 hover:text-gray-700 flex-shrink-0"
            >
              <span className="sr-only">Dismiss</span>
              <X size={16} />
            </button>
          </div>
        </div>
        
        {/* Expanded Content */}
        {isExpanded && (
          <div className="mt-3">
            <p className="text-sm text-gray-700 mb-3">{announcement.content}</p>
            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-1 text-xs text-gray-500">
                <Award size={14} />
                <span>
                  {announcement.type === "feature" && "New Feature"}
                  {announcement.type === "promotion" && "Limited Offer"}
                  {announcement.type === "security" && "Important Update"}
                  {announcement.type === "event" && "Upcoming Event"}
                </span>
              </div>
              <button className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-md transition-colors">
                {announcement.action}
              </button>
            </div>
          </div>
        )}
        
        {/* Progress bar for rotating announcements */}
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-100">
          <div 
            className="h-full bg-indigo-500 transition-all duration-100 ease-out"
            style={{ width: `${(currentAnnouncement + 1) * (100 / announcements.length)}%` }}
          />
        </div>
      </div>
      
      {/* Announcement Navigation Dots */}
      {announcements.length > 1 && (
        <div className="flex justify-center mt-2 space-x-1">
          {announcements.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentAnnouncement(index)}
              className={`w-2 h-2 rounded-full transition-all ${
                currentAnnouncement === index ? 'bg-indigo-600 w-4' : 'bg-gray-300'
              }`}
            >
              <span className="sr-only">Announcement {index + 1}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default AnnouncementBanner;