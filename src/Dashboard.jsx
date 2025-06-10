import React from 'react';
import './Dashboard.css';
import Sidebar from './components/Sidebar';
import { Outlet } from 'react-router-dom';

function Dashboard() {
  return (
    <div className="dashboard-layout">
      <Sidebar />
      <main className="dashboard-main">
        <Outlet />
      </main>
    </div>
  );
}

export default Dashboard; 