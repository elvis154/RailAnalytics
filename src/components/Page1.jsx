import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import Table from './Table';
const Page1 = () => {
  const chartRef = useRef();
  const [currentChart, setCurrentChart] = useState(0);
  const [selectedYear, setSelectedYear] = useState('2024');

  // Sample data for different years
  const chartData = {
    2024: {
      line: [
        { month: 'Jan', value: 65 },
        { month: 'Feb', value: 59 },
        { month: 'Mar', value: 80 },
        { month: 'Apr', value: 81 },
        { month: 'May', value: 56 },
        { month: 'Jun', value: 55 },
        { month: 'Jul', value: 40 },
        { month: 'Aug', value: 45 },
        { month: 'Sep', value: 60 },
        { month: 'Oct', value: 75 },
        { month: 'Nov', value: 85 },
        { month: 'Dec', value: 90 }
      ],
      bar: [
        { category: 'Product A', value: 45 },
        { category: 'Product B', value: 68 },
        { category: 'Product C', value: 32 },
        { category: 'Product D', value: 56 },
        { category: 'Product E', value: 78 }
      ]
    },
    2023: {
      line: [
        { month: 'Jan', value: 55 },
        { month: 'Feb', value: 62 },
        { month: 'Mar', value: 70 },
        { month: 'Apr', value: 75 },
        { month: 'May', value: 68 },
        { month: 'Jun', value: 72 },
        { month: 'Jul', value: 58 },
        { month: 'Aug', value: 65 },
        { month: 'Sep', value: 78 },
        { month: 'Oct', value: 82 },
        { month: 'Nov', value: 88 },
        { month: 'Dec', value: 95 }
      ],
      bar: [
        { category: 'Product A', value: 38 },
        { category: 'Product B', value: 72 },
        { category: 'Product C', value: 28 },
        { category: 'Product D', value: 62 },
        { category: 'Product E', value: 85 }
      ]
    },
    2022: {
      line: [
        { month: 'Jan', value: 45 },
        { month: 'Feb', value: 52 },
        { month: 'Mar', value: 48 },
        { month: 'Apr', value: 58 },
        { month: 'May', value: 65 },
        { month: 'Jun', value: 68 },
        { month: 'Jul', value: 72 },
        { month: 'Aug', value: 75 },
        { month: 'Sep', value: 70 },
        { month: 'Oct', value: 68 },
        { month: 'Nov', value: 72 },
        { month: 'Dec', value: 78 }
      ],
      bar: [
        { category: 'Product A', value: 42 },
        { category: 'Product B', value: 58 },
        { category: 'Product C', value: 35 },
        { category: 'Product D', value: 48 },
        { category: 'Product E', value: 65 }
      ]
    }
  };

  const chartTitles = ['Monthly Performance Trend', 'Product Performance Analysis'];
  const years = ['2024', '2023', '2022'];

  useEffect(() => {
    drawChart();
  }, [currentChart, selectedYear]);

  const drawChart = () => {
    if (currentChart === 0) {
      drawLineChart();
    } else {
      drawBarChart();
    }
  };

  const drawLineChart = () => {
    const svg = d3.select(chartRef.current);
    svg.selectAll("*").remove();

    const margin = { top: 40, right: 40, bottom: 60, left: 70 };
    const width = 680 - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    const chart = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    const lineData = chartData[selectedYear].line;

    // Scales
    const x = d3.scaleBand()
      .domain(lineData.map(d => d.month))
      .range([0, width])
      .padding(0.2);

    const y = d3.scaleLinear()
      .domain([0, d3.max(lineData, d => d.value) + 10])
      .range([height, 0]);

    // Minimal grid lines
    chart.selectAll('.grid-line-y')
      .data(y.ticks(5))
      .enter().append('line')
      .attr('class', 'grid-line-y')
      .attr('x1', 0)
      .attr('x2', width)
      .attr('y1', d => y(d))
      .attr('y2', d => y(d))
      .attr('stroke', '#f8fafc')
      .attr('stroke-width', 1);

    // Area under the line - very subtle
    const area = d3.area()
      .x(d => x(d.month) + x.bandwidth() / 2)
      .y0(height)
      .y1(d => y(d.value))
      .curve(d3.curveCatmullRom.alpha(0.5));

    chart.append('path')
      .datum(lineData)
      .attr('fill', '#6366f1')
      .attr('fill-opacity', 0.03)
      .attr('d', area);

    // Line
    const line = d3.line()
      .x(d => x(d.month) + x.bandwidth() / 2)
      .y(d => y(d.value))
      .curve(d3.curveCatmullRom.alpha(0.5));

    const path = chart.append('path')
      .datum(lineData)
      .attr('fill', 'none')
      .attr('stroke', '#6366f1')
      .attr('stroke-width', 2)
      .attr('d', line)
      .attr('stroke-dasharray', function() {
        return this.getTotalLength();
      })
      .attr('stroke-dashoffset', function() {
        return this.getTotalLength();
      })
      .transition()
      .duration(1200)
      .ease(d3.easeQuadOut)
      .attr('stroke-dashoffset', 0);

    // Data points
    chart.selectAll('.dot')
      .data(lineData)
      .enter().append('circle')
      .attr('class', 'dot')
      .attr('cx', d => x(d.month) + x.bandwidth() / 2)
      .attr('cy', d => y(d.value))
      .attr('r', 0)
      .attr('fill', '#6366f1')
      .attr('stroke', '#ffffff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .transition()
      .delay((d, i) => i * 60)
      .duration(300)
      .attr('r', 3);

    // Hover interactions
    chart.selectAll('.dot')
      .on('mouseover', function(event, d) {
        d3.select(this)
          .transition()
          .duration(150)
          .attr('r', 5)
          .attr('fill', '#4f46e5');

        // Tooltip
        chart.append('g')
          .attr('class', 'tooltip')
          .append('rect')
          .attr('x', x(d.month) + x.bandwidth() / 2 - 20)
          .attr('y', y(d.value) - 30)
          .attr('width', 40)
          .attr('height', 20)
          .attr('fill', '#1f2937')
          .attr('rx', 3)
          .attr('opacity', 0)
          .transition()
          .duration(150)
          .attr('opacity', 0.9);

        chart.select('.tooltip')
          .append('text')
          .attr('x', x(d.month) + x.bandwidth() / 2)
          .attr('y', y(d.value) - 16)
          .attr('text-anchor', 'middle')
          .style('font-size', '11px')
          .style('font-weight', '500')
          .style('fill', '#ffffff')
          .style('opacity', 0)
          .text(d.value)
          .transition()
          .duration(150)
          .style('opacity', 1);
      })
      .on('mouseout', function(event, d) {
        d3.select(this)
          .transition()
          .duration(150)
          .attr('r', 3)
          .attr('fill', '#6366f1');

        chart.selectAll('.tooltip')
          .transition()
          .duration(150)
          .style('opacity', 0)
          .remove();
      });

    // Axes
    chart.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x))
      .selectAll('text')
      .style('font-size', '11px')
      .style('font-weight', '400')
      .style('fill', '#6b7280');

    chart.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(y).ticks(5).tickFormat(d => d))
      .selectAll('text')
      .style('font-size', '11px')
      .style('font-weight', '400')
      .style('fill', '#6b7280');

    // Clean up axis lines
    chart.selectAll('.domain').attr('stroke', '#e5e7eb').attr('stroke-width', 1);
    chart.selectAll('.tick line').attr('stroke', '#e5e7eb').attr('stroke-width', 1);

    // Y-axis label
    chart.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -45)
      .attr('x', -height / 2)
      .attr('text-anchor', 'middle')
      .style('font-size', '12px')
      .style('fill', '#9ca3af')
      .style('font-weight', '400')
      .text('Performance Score');
  };

  const drawBarChart = () => {
    const svg = d3.select(chartRef.current);
    svg.selectAll("*").remove();

    const margin = { top: 40, right: 40, bottom: 60, left: 70 };
    const width = 680 - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    const chart = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    const barData = chartData[selectedYear].bar;

    // Scales
    const x = d3.scaleBand()
      .domain(barData.map(d => d.category))
      .range([0, width])
      .padding(0.4);

    const y = d3.scaleLinear()
      .domain([0, d3.max(barData, d => d.value) + 10])
      .range([height, 0]);

    // Minimal grid lines
    chart.selectAll('.grid-line-y')
      .data(y.ticks(5))
      .enter().append('line')
      .attr('class', 'grid-line-y')
      .attr('x1', 0)
      .attr('x2', width)
      .attr('y1', d => y(d))
      .attr('y2', d => y(d))
      .attr('stroke', '#f8fafc')
      .attr('stroke-width', 1);

    // Bars
    chart.selectAll('.bar')
      .data(barData)
      .enter().append('rect')
      .attr('class', 'bar')
      .attr('x', d => x(d.category))
      .attr('y', height)
      .attr('width', x.bandwidth())
      .attr('height', 0)
      .attr('fill', '#6366f1')
      .attr('rx', 2)
      .style('cursor', 'pointer')
      .transition()
      .delay((d, i) => i * 100)
      .duration(600)
      .ease(d3.easeQuadOut)
      .attr('y', d => y(d.value))
      .attr('height', d => height - y(d.value));

    // Value labels
    chart.selectAll('.label')
      .data(barData)
      .enter().append('text')
      .attr('class', 'label')
      .attr('x', d => x(d.category) + x.bandwidth() / 2)
      .attr('y', height)
      .attr('text-anchor', 'middle')
      .style('font-size', '11px')
      .style('font-weight', '500')
      .style('fill', '#6b7280')
      .style('opacity', 0)
      .text(d => d.value)
      .transition()
      .delay((d, i) => i * 100 + 300)
      .duration(300)
      .attr('y', d => y(d.value) - 8)
      .style('opacity', 1);

    // Hover effects
    chart.selectAll('.bar')
      .on('mouseover', function(event, d) {
        d3.select(this)
          .transition()
          .duration(150)
          .attr('fill', '#4f46e5')
          .style('opacity', 0.8);
      })
      .on('mouseout', function(event, d) {
        d3.select(this)
          .transition()
          .duration(150)
          .attr('fill', '#6366f1')
          .style('opacity', 1);
      });

    // Axes
    chart.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x))
      .selectAll('text')
      .style('font-size', '11px')
      .style('font-weight', '400')
      .style('fill', '#6b7280');

    chart.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(y).ticks(5).tickFormat(d => d))
      .selectAll('text')
      .style('font-size', '11px')
      .style('font-weight', '400')
      .style('fill', '#6b7280');

    // Clean up axis lines
    chart.selectAll('.domain').attr('stroke', '#e5e7eb').attr('stroke-width', 1);
    chart.selectAll('.tick line').attr('stroke', '#e5e7eb').attr('stroke-width', 1);

    // Y-axis label
    chart.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -45)
      .attr('x', -height / 2)
      .attr('text-anchor', 'middle')
      .style('font-size', '12px')
      .style('fill', '#9ca3af')
      .style('font-weight', '400')
      .text('Performance Score');
  };

  const nextChart = () => {
    setCurrentChart((prev) => (prev + 1) % chartTitles.length);
  };

  const prevChart = () => {
    setCurrentChart((prev) => (prev - 1 + chartTitles.length) % chartTitles.length);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6 font-sans">
      <style jsx>{`
        .dashboard-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
          background: white;
          border-radius: 8px;
          padding: 20px 28px;
          border: 1px solid #e5e7eb;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }
        
        .dashboard-title {
          color: #111827;
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0;
          letter-spacing: -0.025em;
        }
        
        .year-selector {
          display: flex;
          align-items: center;
          gap: 6px;
          background: #f9fafb;
          padding: 6px 10px;
          border-radius: 6px;
          border: 1px solid #e5e7eb;
        }
        
        .year-dropdown {
          border: none;
          background: transparent;
          font-size: 13px;
          font-weight: 500;
          color: #374151;
          cursor: pointer;
          outline: none;
          padding: 2px 6px;
        }
        
        .chart-container {
          max-width: 1000px;
          margin: 0 auto;
          background: white;
          border-radius: 8px;
          padding: 28px;
          border: 1px solid #e5e7eb;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }
        
        .chart-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
          padding-bottom: 12px;
          border-bottom: 1px solid #f3f4f6;
        }
        
        .chart-title {
          font-size: 1.125rem;
          font-weight: 500;
          color: #111827;
          margin: 0;
          text-align: center;
          flex-grow: 1;
          letter-spacing: -0.025em;
        }
        
        .nav-button {
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          padding: 6px;
          cursor: pointer;
          transition: all 0.15s ease;
          color: #6b7280;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        
        .nav-button:hover:not(:disabled) {
          background: #f3f4f6;
          border-color: #d1d5db;
          color: #374151;
        }
        
        .nav-button:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }
        
        .chart-wrapper {
          display: flex;
          justify-content: center;
          margin-bottom: 16px;
          background: #fefefe;
          border-radius: 4px;
          padding: 16px;
        }
        
        .chart-indicators {
          display: flex;
          justify-content: center;
          gap: 6px;
        }
        
        .indicator {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          border: none;
          background: #d1d5db;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        
        .indicator.active {
          background: #6366f1;
          transform: scale(1.2);
        }
        
        .indicator:hover {
          background: #9ca3af;
        }
        
        .indicator.active:hover {
          background: #4f46e5;
        }
        
        @media (max-width: 768px) {
          .dashboard-header {
            flex-direction: column;
            gap: 12px;
          }
          
          .chart-container {
            margin: 12px;
            padding: 20px;
          }
          
          .chart-header {
            flex-direction: column;
            gap: 8px;
          }
        }
      `}</style>

      {/* Header */}
      <div className="dashboard-header">
        <h1 className="dashboard-title">Performance Analytics</h1>
        <div className="year-selector">
          <Calendar size={16} color="#6b7280" />
          <select 
            value={selectedYear} 
            onChange={(e) => setSelectedYear(e.target.value)}
            className="year-dropdown"
          >
            {years.map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Chart */}
      <div className="chart-container">
        <div className="chart-header">
          <button 
            onClick={prevChart} 
            className="nav-button"
            disabled={currentChart === 0}
          >
            <ChevronLeft size={18} />
          </button>
          
          <h2 className="chart-title">
            {chartTitles[currentChart]} • {selectedYear}
          </h2>
          
          <button 
            onClick={nextChart} 
            className="nav-button"
            disabled={currentChart === chartTitles.length - 1}
          >
            <ChevronRight size={18} />
          </button>
        </div>

        <div className="chart-wrapper">
          <svg ref={chartRef} width={720} height={440} />
        </div>

        <div className="chart-indicators">
          {chartTitles.map((_, index) => (
            <button
              key={index}
              className={`indicator ${currentChart === index ? 'active' : ''}`}
              onClick={() => setCurrentChart(index)}
            />
          ))}
        </div>
        <Table/>
      </div>
    </div>
  );
};

export default Page1;