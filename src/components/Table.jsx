import * as React from 'react';
import Paper from '@mui/material/Paper';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';

const columns = [
  { id: 'srNo', label: 'Sr.No', minWidth: 50, align: 'center' },
  { id: 'particulars', label: 'Particulars', minWidth: 300 },
  { id: 'value', label: 'Value', minWidth: 150, align: 'right', format: (value) => value.toLocaleString('en-US') },
  { id: 'percentageVar', label: '% var w.r.t PY', minWidth: 120, align: 'right', format: (value) => `${value.toFixed(2)}%` },
];

const fiscalYears = [
  '2019-20',
  '2020-21',
  '2021-22',
  '2022-23',
  '2023-24',
  '2024-25',
];

// Dummy data based on the report structure
const rows = [
  { 
    srNo: 1, 
    particulars: 'Loading', 
    values: { 
      '2019-20': 77.259, 
      '2020-21': 80.913, 
      '2021-22': 88.067, 
      '2022-23': 108.152, 
      '2023-24': 104.952, 
      '2024-25': 7.953 
    }, 
    percentageVar: { 
      '2019-20': -3.370, 
      '2020-21': 4.720, 
      '2021-22': 8.800, 
      '2022-23': 22.840, 
      '2023-24': -2.970, 
      '2024-25': 0 
    } 
  },
  { 
    srNo: 2, 
    particulars: 'Originating Revenue', 
    values: { 
      '2019-20': 101335.84, 
      '2020-21': 10041.84, 
      '2021-22': 10868.74, 
      '2022-23': 14820.66, 
      '2023-24': 11435, 
      '2024-25': 1099.1 
    }, 
    percentageVar: { 
      '2019-20': -7.560, 
      '2020-21': -90.090, 
      '2021-22': 8.220, 
      '2022-23': 36.320, 
      '2023-24': -22.840, 
      '2024-25': 0 
    } 
  },
  { 
    srNo: 3, 
    particulars: 'Apportioned Revenue (Outward Retained Share)', 
    values: { 
      '2019-20': 446.58, 
      '2020-21': 433.87, 
      '2021-22': 4746.3, 
      '2022-23': 6230.42, 
      '2023-24': 484.98, 
      '2024-25': 375.23 
    }, 
    percentageVar: { 
      '2019-20': -2.010, 
      '2020-21': -2.840, 
      '2021-22': 993.740, 
      '2022-23': 31.230, 
      '2023-24': -92.220, 
      '2024-25': 0 
    } 
  },
  { 
    srNo: 4, 
    particulars: 'Apportioned Revenue (Inward Share) (3+4)', 
    values: { 
      '2019-20': 295.08, 
      '2020-21': 267.35, 
      '2021-22': 3972.43, 
      '2022-23': 4191.41, 
      '2023-24': 327.84, 
      '2024-25': 372.61 
    }, 
    percentageVar: { 
      '2019-20': 13.660, 
      '2020-21': -9.390, 
      '2021-22': 1385.820, 
      '2022-23': 5.520, 
      '2023-24': -92.180, 
      '2024-25': 0 
    } 
  },
  { 
    srNo: 5, 
    particulars: 'Total Apportioned Revenue (3+4)', 
    values: { 
      '2019-20': 739.36, 
      '2020-21': 705.92, 
      '2021-22': 8718.71, 
      '2022-23': 10421.43, 
      '2023-24': 812.82, 
      '2024-25': 747.82 
    }, 
    percentageVar: { 
      '2019-20': 4.310, 
      '2020-21': -4.520, 
      '2021-22': 1134.940, 
      '2022-23': 19.510, 
      '2023-24': -92.200, 
      '2024-25': 0 
    } 
  },
  { 
    srNo: 6, 
    particulars: 'Ratio of Apportioned to Originating Revenue (5/2)', 
    values: { 
      '2019-20': 72.95, 
      '2020-21': 70.3, 
      '2021-22': 80.22, 
      '2022-23': 70.32, 
      '2023-24': 71.84, 
      '2024-25': 77.14 
    }, 
    percentageVar: { 
      '2019-20': 0, 
      '2020-21': -3.630, 
      '2021-22': 14.110, 
      '2022-23': -12.340, 
      '2023-24': 2.160, 
      '2024-25': 0 
    } 
  },
  { 
    srNo: 7, 
    particulars: 'Ratio of Outward Retained Share to Originating Revenue (3/2)', 
    values: { 
      '2019-20': 44.09, 
      '2020-21': 43.66, 
      '2021-22': 43.67, 
      '2022-23': 42.04, 
      '2023-24': 40.98, 
      '2024-25': 73.24 
    }, 
    percentageVar: { 
      '2019-20': 0, 
      '2020-21': -0.970, 
      '2021-22': 0.020, 
      '2022-23': -3.730, 
      '2023-24': -2.520, 
      '2024-25': 0 
    } 
  },
  { 
    srNo: 8, 
    particulars: 'Ratio of Outward Retained Share to Total Apportioned Revenue (3/5)', 
    values: { 
      '2019-20': 60.44, 
      '2020-21': 62.1, 
      '2021-22': 54.44, 
      '2022-23': 59.78, 
      '2023-24': 59.67, 
      '2024-25': 56.05 
    }, 
    percentageVar: { 
      '2019-20': 0, 
      '2020-21': 2.750, 
      '2021-22': -12.300, 
      '2022-23': 9.810, 
      '2023-24': -0.180, 
      '2024-25': 0 
    } 
  },
  { 
    srNo: 9, 
    particulars: 'Ratio of Inward Share to Total Apportioned Revenue (4/5)', 
    values: { 
      '2019-20': 39.56, 
      '2020-21': 37.9, 
      '2021-22': 45.56, 
      '2022-23': 40.22, 
      '2023-24': 40.33, 
      '2024-25': 43.95 
    }, 
    percentageVar: { 
      '2019-20': 0, 
      '2020-21': -4.200, 
      '2021-22': 20.210, 
      '2022-23': -11.720, 
      '2023-24': 0.270, 
      '2024-25': 0 
    } 
  },
];

export default function StickyHeadTable() {
  const [selectedYear, setSelectedYear] = React.useState('2023-24');

  const handleYearChange = (event) => {
    setSelectedYear(event.target.value);
  };

  return (
    <Paper sx={{ width: '100%', overflow: 'hidden', padding: 2 }}>
      <FormControl sx={{ minWidth: 120, marginBottom: 2 }}>
        <InputLabel id="year-select-label">Fiscal Year</InputLabel>
        <Select
          labelId="year-select-label"
          id="year-select"
          value={selectedYear}
          label="Fiscal Year"
          onChange={handleYearChange}
        >
          {fiscalYears.map((year) => (
            <MenuItem key={year} value={year}>
              {year}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <TableContainer sx={{ maxHeight: 440 }}>
        <Table stickyHeader aria-label="sticky table">
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell
                  key={column.id}
                  align={column.align}
                  style={{ minWidth: column.minWidth, backgroundColor: '#e0e0e0', fontWeight: 'bold' }}
                >
                  {column.label}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => (
              <TableRow hover role="checkbox" tabIndex={-1} key={row.srNo}>
                <TableCell align="center">{row.srNo}</TableCell>
                <TableCell>{row.particulars}</TableCell>
                <TableCell align="right">
                  {columns.find(col => col.id === 'value')?.format?.(row.values[selectedYear]) || row.values[selectedYear]}
                </TableCell>
                <TableCell align="right">
                  {columns.find(col => col.id === 'percentageVar')?.format?.(row.percentageVar[selectedYear]) || row.percentageVar[selectedYear]}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}