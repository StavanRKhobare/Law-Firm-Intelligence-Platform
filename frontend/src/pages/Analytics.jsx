import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import { tokens } from '../theme';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { analyticsAPI } from '../services/api';

// Validated categorical palette (dataviz skill). Colour follows the status, not its position.
const STATUS_COLORS = { Filed: '#2a78d6', Hearing: '#eb6834', Pending: '#1baf7a', Disposed: '#eda100' };
const OTHER_COLOR = '#e87ba4';

export default function Analytics() {
  const [loading, setLoading] = useState(true);
  const [casesByStatus, setCasesByStatus] = useState([]);
  const [crimeTypes, setCrimeTypes] = useState([]);
  const [hotspots, setHotspots] = useState([]);
  const [officers, setOfficers] = useState([]);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const [statusRes, typesRes, hotspotsRes, officersRes] = await Promise.all([
        analyticsAPI.getCasesByStatus(),
        analyticsAPI.getMatterTypes({ limit: 5 }),
        analyticsAPI.getCaseload({ limit: 5 }),
        analyticsAPI.getLawyerPerformance({ limit: 10 }),
      ]);
      
      setCasesByStatus(statusRes.data);
      setCrimeTypes(typesRes.data);
      setHotspots(hotspotsRes.data);
      setOfficers(officersRes.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
        Analytics & Reports
      </Typography>

      <Grid container spacing={3}>
        {/* Cases by Status */}
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Cases by Status
            </Typography>
            <ResponsiveContainer width="100%" height="90%">
              <PieChart>
                <Pie
                  data={casesByStatus}
                  dataKey="count"
                  nameKey="status"
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  stroke="#fff"
                  strokeWidth={2}
                  label={({ status, count }) => `${status}: ${count}`}
                >
                  {casesByStatus.map((entry) => (
                    <Cell key={entry.status} fill={STATUS_COLORS[entry.status] || OTHER_COLOR} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend formatter={(value) => <span style={{ color: tokens.foreground }}>{value}</span>} />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Crime Types */}
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Matter types
            </Typography>
            <ResponsiveContainer width="100%" height="90%">
              <BarChart data={crimeTypes}>
                <CartesianGrid vertical={false} stroke={tokens.muted} />
                <XAxis dataKey="matter_type" axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: tokens.muted }} />
                <Bar dataKey="count" name="Matters" fill={tokens.primary} radius={[4, 4, 0, 0]} maxBarSize={48} />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Crime Hotspots */}
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Caseload by locality
            </Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell><strong>Location</strong></TableCell>
                    <TableCell><strong>City</strong></TableCell>
                    <TableCell align="right"><strong>Matters</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {hotspots.map((spot) => (
                    <TableRow key={spot.location_id}>
                      <TableCell>{spot.landmark || 'Unknown'}</TableCell>
                      <TableCell>{spot.city || 'N/A'}</TableCell>
                      <TableCell align="right">{spot.matter_count}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>

        {/* Officer Performance */}
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Lawyer workload (top 10)
            </Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell><strong>Lawyer</strong></TableCell>
                    <TableCell align="right"><strong>Cases</strong></TableCell>
                    <TableCell align="right"><strong>Disposed</strong></TableCell>
                    <TableCell align="right"><strong>Rate</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {officers.map((officer) => (
                    <TableRow key={officer.lawyer_id}>
                      <TableCell>
                        <Typography variant="body2">
                          {officer.lawyer_name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {officer.designation}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">{officer.total_cases}</TableCell>
                      <TableCell align="right">{officer.disposed_cases}</TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          color={officer.disposal_rate > 50 ? 'success.main' : 'warning.main'}
                        >
                          {officer.disposal_rate}%
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}