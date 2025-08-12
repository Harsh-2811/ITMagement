// Import necessary libraries and components
import { useState } from "react";
import { Menu, Bell, Calendar, Users, TrendingUp, Folder, ListChecks, BarChart2, FileText, Settings } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Layout from "@/components/Layout"; // Import the Layout component
import { useResponsive } from "@/hooks/useResponsive"; // Import the custom hook

// Define the Dashboard component
export default function Dashboard() {
  // Use the useResponsive hook to get screen size information
  const { isMobile, isTablet, isDesktop } = useResponsive();

  // Sample data for dashboard statistics
  const stats = [
    {
      title: "Total Users",
      value: "2,543",
      icon: <Users size={24} />,
      change: "+12%",
      changeType: "positive"
    },
    {
      title: "Revenue",
      value: "$45,231",
      icon: <TrendingUp size={24} />,
      change: "+8%",
      changeType: "positive"
    },
    {
      title: "Projects",
      value: "127",
      icon: <Folder size={24} />,
      change: "+23%",
      changeType: "positive"
    },
    {
      title: "Tasks",
      value: "1,429",
      icon: <ListChecks size={24} />,
      change: "-2%",
      changeType: "negative"
    },
  ];

  // Sample data for recent activities
  const recentActivity = [
    { action: "User John Doe registered", time: "2 minutes ago", type: "user" },
    { action: "Project Alpha completed", time: "1 hour ago", type: "project" },
    { action: "New task assigned to team", time: "3 hours ago", type: "task" },
    { action: "Monthly report generated", time: "1 day ago", type: "report" },
    { action: "System backup completed", time: "2 days ago", type: "system" },
  ];

  // Sample data for quick actions
  const quickActions = [
    { title: "New Project", description: "Create a new project", icon: <Folder size={18} /> },
    { title: "Add User", description: "Invite team member", icon: <Users size={18} /> },
    { title: "Generate Report", description: "Export data", icon: <FileText size={18} /> },
    { title: "Settings", description: "Configure app", icon: <Settings size={18} /> },
  ];

  // Sample data for system status
  const systemStatus = [
    { name: "Server Status", status: "Online", statusType: "success" },
    { name: "Database", status: "Connected", statusType: "success" },
    { name: "Storage", status: "75% Used", statusType: "warning" },
    { name: "API Status", status: "Operational", statusType: "success" },
  ];

  return (
    <Layout title="Dashboard">
      <div className="space-y-6">
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
              Dashboard Overview
            </h1>
            <p className="text-gray-600 dark:text-gray-300 mt-1">
              Welcome back! Here's what's happening today.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {!isMobile && (
              <Button variant="outline" size="sm" className="hidden sm:flex">
                <Calendar size={16} className="mr-2" />
                Last 30 days
              </Button>
            )}
            <Button variant="outline" size="sm">
              <Bell size={16} className="mr-2" />
              {!isMobile && <span className="hidden sm:inline">Notifications</span>}
            </Button>
          </div>
        </div>

        {/* Stats Grid - Display key statistics */}
        <div className={`grid ${isMobile ? 'grid-cols-1' : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4'} gap-4 lg:gap-6`}>
          {stats.map((stat, index) => (
            <Card key={index} className="hover:shadow-lg transition-shadow">
              <CardContent className="p-4 lg:p-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                      {stat.title}
                    </p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                      {stat.value}
                    </p>
                    <p className={`text-sm mt-1 ${
                      stat.changeType === 'positive' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {stat.change} from last month
                    </p>
                  </div>
                  <div className="h-12 w-12 bg-violet-100 dark:bg-violet-900 rounded-lg flex items-center justify-center text-violet-600 dark:text-violet-400 flex-shrink-0">
                    {stat.icon}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Main Content Grid - Performance Overview and Recent Activity */}
        <div className={`grid ${isMobile ? 'grid-cols-1' : 'xl:grid-cols-3'} gap-6`}>
          {/* Chart Area - Placeholder for a performance chart */}
          <Card className={`${!isMobile && 'xl:col-span-2'}`}>
            <CardHeader>
              <CardTitle>Performance Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64 sm:h-80 bg-gray-50 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                <div className="text-center">
                  <BarChart2 size={48} className="mx-auto text-gray-400 mb-4" />
                  <p className="text-gray-500 dark:text-gray-400">Chart placeholder</p>
                  <p className="text-sm text-gray-400 dark:text-gray-500">
                    Integration with charting library needed
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity - List of recent activities */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="space-y-4 p-6 max-h-96 overflow-y-auto">
                {recentActivity.map((activity, index) => (
                  <div key={index} className="flex items-start space-x-3">
                    <div className="h-8 w-8 bg-violet-100 dark:bg-violet-900 rounded-full flex items-center justify-center flex-shrink-0">
                      <div className="h-2 w-2 bg-violet-600 rounded-full"></div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {activity.action}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {activity.time}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Additional Content Row - Quick Actions and System Status */}
        <div className={`grid ${isMobile ? 'grid-cols-1' : 'md:grid-cols-2'} gap-6`}>
          {/* Quick Actions - Buttons for common actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {quickActions.map((action, index) => (
                  <Button
                    key={index}
                    variant={index === 0 ? "default" : "outline"}
                    className="justify-start h-auto py-3"
                  >
                    <span className="mr-2">{action.icon}</span>
                    <span className="text-left">
                      <div className="font-medium">{action.title}</div>
                      <div className="text-xs opacity-75">{action.description}</div>
                    </span>
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* System Status - Overview of system status */}
          <Card>
            <CardHeader>
              <CardTitle>System Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {systemStatus.map((system, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {system.name}
                    </span>
                    <span className={`flex items-center text-sm ${
                      system.statusType === 'success'
                        ? 'text-green-600'
                        : system.statusType === 'warning'
                        ? 'text-yellow-600'
                        : 'text-red-600'
                    }`}>
                      <div className={`h-2 w-2 rounded-full mr-2 ${
                        system.statusType === 'success'
                          ? 'bg-green-600'
                          : system.statusType === 'warning'
                          ? 'bg-yellow-600'
                          : 'bg-red-600'
                      }`}></div>
                      {system.status}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
}
