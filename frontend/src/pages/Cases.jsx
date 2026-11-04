import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  CircularProgress,
  TextField,
  InputAdornment,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
} from '@mui/material';
import { Search } from '@mui/icons-material';
import { casesAPI } from '../services/api';
import StatusChip from '../components/StatusChip';

export default function Cases() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    fetchCases();
  }, [page, rowsPerPage, search, statusFilter]);

  const fetchCases = async () => {
    try {
      setLoading(true);
      const params = {
        page: page + 1,
        size: rowsPerPage,
        ...(search && { search }),
        ...(statusFilter && { status: statusFilter }),
      };
      const response = await casesAPI.getAll(params);
      setCases(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      console.error('Error fetching cases:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
        Matters
      </Typography>

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <TextField
            placeholder="Search by title or case number..."
            variant="outlined"
            size="small"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            sx={{ flexGrow: 1, minWidth: 250 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
          />
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="Filed">Filed</MenuItem>
              <MenuItem value="Hearing">Hearing</MenuItem>
              <MenuItem value="Pending">Pending</MenuItem>
              <MenuItem value="Disposed">Disposed</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Paper>

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Case No</TableCell>
              <TableCell>Title</TableCell>
              <TableCell>Cause date</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Lead counsel</TableCell>
              <TableCell>Court</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 5 }}>
                  <CircularProgress />
                </TableCell>
              </TableRow>
            ) : cases.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 5 }}>
                  <Typography color="text.secondary">No cases found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              cases.map((caseItem) => (
                <TableRow key={caseItem.case_id} hover>
                  <TableCell>{caseItem.case_number}</TableCell>
                  <TableCell>{caseItem.matter_title}</TableCell>
                  <TableCell>{new Date(caseItem.date_cause).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <StatusChip status={caseItem.status} />
                  </TableCell>
                  <TableCell>{caseItem.lead_counsel || 'Unassigned'}</TableCell>
                  <TableCell>{caseItem.court_name || 'N/A'}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={total}
          page={page}
          onPageChange={handleChangePage}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          rowsPerPageOptions={[5, 10, 25, 50]}
        />
      </TableContainer>
    </Box>
  );
}