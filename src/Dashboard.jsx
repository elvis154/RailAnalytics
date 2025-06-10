import React from 'react';
import './Dashboard.css';
import Sidebar from './components/Sidebar';
import { Outlet, useLocation } from 'react-router-dom';
import StickyHeadTable from './components/Table';

function Dashboard() {
  const location = useLocation();

  return (
    <div className="dashboard-layout">
      <Sidebar />
      <main className="dashboard-main">
        {/* Show StickyHeadTable only on the main /dashboard route */}
        {location.pathname === '/dashboard' ? (
          <div className="dashboard-container">
            <h1>RailAnalytics Dashboard</h1>
            <StickyHeadTable />
          </div>
        ) : (
          <Outlet />
        )}
      </main>
    </div>
  );
}

export default Dashboard;