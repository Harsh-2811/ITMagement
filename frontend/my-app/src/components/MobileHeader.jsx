// Import necessary icons and UI components
import { Menu, Bell, Search } from "lucide-react";
import { Button } from "@/components/ui/button";

// Define the MobileHeader component with props for handling menu clicks and setting the title

export default function MobileHeader({ onMenuClick, title = "Dashboard" }) {
  return (

    // Header element specifically for mobile view, hidden on larger screens
    <header className="lg:hidden bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 sticky top-0 z-30">
      {/* Container for header content */}
      <div className="flex items-center justify-between px-4 py-3">
        
        {/* Left side of the header: Menu button and title */}
        <div className="flex items-center space-x-3">
          {/* Button to open the sidebar menu */}

          <Button
            variant="ghost"
            size="sm"
            onClick={onMenuClick}
            className="text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <Menu size={20} />
          </Button>
          {/* Title of the current page */}
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
            {title}
          </h1>
        </div>

        {/* Right side of the header: Search and Notification buttons */}
        <div className="flex items-center space-x-2">
          {/* Search button */}
          <Button
            variant="ghost"
            size="sm"
            className="text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <Search size={18} />
          </Button>
          {/* Notification button with a badge showing the number of notifications */}
          <Button
            variant="ghost"
            size="sm"
            className="text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 relative"
          >
            <Bell size={18} />

            {/* Notification badge showing the count of new notifications */}
            <span className="absolute -top-1 -right-1 h-4 w-4 bg-red-500 rounded-full flex items-center justify-center text-xs text-white">
              3
            </span>
          </Button>
        </div>
      </div>
    </header>
  );
}
