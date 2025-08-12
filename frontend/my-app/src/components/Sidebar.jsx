// src/components/Sidebar.jsx
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Home,
  Folder,
  ListChecks,
  Settings,
  LogOut,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useMutation } from "@tanstack/react-query";
import client from "@/api/client";

export default function Sidebar({ isOpen, onClose }) {
  const [openMenus, setOpenMenus] = useState({});
  const location = useLocation();
  const navigate = useNavigate();

  const toggleMenu = (label) => {
    setOpenMenus((prev) => ({ ...prev, [label]: !prev[label] }));
  };

  const handleNavigation = () => {
    if (window.innerWidth < 1024) {
      onClose();
    }
  };

  const refresh = localStorage.getItem("refresh");

  const logoutMutation = useMutation({
    mutationFn: (refresh) => client.post("/logout/", { refresh }),
    onSuccess: () => {
      localStorage.clear();
      navigate("/");
    },
    onError: () => {
      alert("Logout failed");
    },
  });

  const handleLogout = () => {
    console.log("refresh token:", refresh);
    if (refresh) {
      logoutMutation.mutate(refresh);
    } else {
      localStorage.clear();
      navigate("/");
    }
  };

  const menuItems = [
    { label: "Dashboard", icon: <Home size={18} />, path: "/dashboard" },
    { label: "Projects", icon: <Folder size={18} />, path: "/projects" },
    { label: "Tasks", icon: <ListChecks size={18} />, path: "/tasks" },
    { label: "Settings", icon: <Settings size={18} />, path: "/settings" },
  ];

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`
          fixed lg:static top-0 left-0 z-50 h-screen w-64 bg-violet-700 text-white
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? "translate-x-0" : "-translate-x-full"} lg:translate-x-0
          overflow-y-auto
        `}
      >
        <div className="flex items-center justify-between p-4 border-b border-violet-600 sticky top-0 bg-violet-700">
          <h2 className="text-xl font-bold">Admin Panel</h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-white hover:bg-violet-600 lg:hidden"
          >
            <X size={20} />
          </Button>
        </div>

        <nav className="flex-1 pb-20">
          <div className="space-y-2 p-4">
            {menuItems.map((item) => (
              <div key={item.label}>
                <Link to={item.path} onClick={handleNavigation}>
                  <Button
                    variant="ghost"
                    className={`w-full justify-start transition-colors ${
                      location.pathname === item.path
                        ? "bg-violet-600 text-white hover:bg-violet-500"
                        : "text-violet-100 hover:bg-violet-600 hover:text-white"
                    }`}
                  >
                    <span className="mr-3">{item.icon}</span>
                    {item.label}
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        </nav>

        {/* Logout Button */}
        <div className="absolute bottom-3 left-0 right-0 p-4 border-t border-violet-600 bg-violet-700">
          <Button
            variant="ghost"
            className="w-full justify-start text-white hover:bg-violet-600 transition-colors"
            onClick={handleLogout}
            disabled={logoutMutation.isPending}
          >
            <LogOut size={18} className="mr-3" />
            {logoutMutation.isPending ? "Logging out..." : "Logout"}
          </Button>
        </div>
      </aside>
    </>
  );
}
