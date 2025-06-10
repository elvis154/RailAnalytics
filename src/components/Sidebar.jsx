import React from 'react';
import { NavLink } from 'react-router-dom';
import './Sidebar.css';

const Sidebar = () => (
  <aside className="sidebar">
    <div className="sidebar-header">Dashboard</div>
    <nav className="sidebar-nav">
      <NavLink to="display" className={({ isActive }) => isActive ? 'sidebar-link active' : 'sidebar-link'}>Display</NavLink>
      <NavLink to="insert" className={({ isActive }) => isActive ? 'sidebar-link active' : 'sidebar-link'}>Insert</NavLink>
      <NavLink to="edit" className={({ isActive }) => isActive ? 'sidebar-link active' : 'sidebar-link'}>Edit</NavLink>
      <NavLink to="use" className={({ isActive }) => isActive ? 'sidebar-link active' : 'sidebar-link'}>Use</NavLink>
    </nav>
  </aside>
);

export default Sidebar; 