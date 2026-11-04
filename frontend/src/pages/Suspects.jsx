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
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { Search, Warning } from '@mui/icons-material';
import { opposingPartiesAPI } from '../services/api';

export default function Suspects() {
  const [suspects, setSuspects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [criminalRecordFilter, setCriminalRecordFilter] = useState('');

  useEffect(() => {
    fetchSuspects();
  }, [page, rowsPerPage, search, criminalRecordFilter]);

  const fetchSuspects = async () => {
    try {
      setLoading(true);
      const params = {
        page: page + 1,
        size: rowsPerPage,
        ...(search && { search }),
        ...(criminalRecordFilter !== '' && { repeat_party: criminalRecordFilter === 'true' }),
      };
      const response = await opposingPartiesAPI.getAll(params);
      setSuspects(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      console.error('Error fetching suspects:', error);
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
        Opposing parties
      </Typography>

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <TextField
            placeholder="Search by name or email..."
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
            <InputLabel>Repeat party</InputLabel>
            <Select
              value={criminalRecordFilter}
              label="Repeat party"
              onChange={(e) => setCriminalRecordFilter(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="true">Has Record</MenuItem>
              <MenuItem value="false">No Record</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Paper>

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Repeat party</TableCell>
              <TableCell>Total Cases</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 5 }}>
                  <CircularProgress />
                </TableCell>
              </TableRow>
            ) : suspects.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 5 }}>
                  <Typography color="text.secondary">No opposing parties found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              suspects.map((suspect) => (
                <TableRow key={suspect.party_id} hover>
                  <TableCell>{suspect.party_id}</TableCell>
                  <TableCell>
                    <Typography variant="body1">
                      {suspect.fname} {suspect.lname}
                    </Typography>
                  </TableCell>
                  <TableCell>{suspect.email || 'N/A'}</TableCell>
                  <TableCell>
                    {suspect.repeat_party ? (
                      <Chip
                        icon={<Warning />}
                        label="Yes"
                        color="error"
                        size="small"
                      />
                    ) : (
                      <Chip label="No" color="success" size="small" variant="outlined" />
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip label={suspect.total_cases} size="small" color="info" />
                  </TableCell>
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