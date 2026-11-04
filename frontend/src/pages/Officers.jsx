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
} from '@mui/material';
import { Search } from '@mui/icons-material';
import { lawyersAPI } from '../services/api';

export default function Officers() {
  const [officers, setOfficers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchOfficers();
  }, [page, rowsPerPage, search]);

  const fetchOfficers = async () => {
    try {
      setLoading(true);
      const params = {
        page: page + 1,
        size: rowsPerPage,
        ...(search && { search }),
      };
      const response = await lawyersAPI.getAll(params);
      setOfficers(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      console.error('Error fetching officers:', error);
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
        Lawyers
      </Typography>

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <TextField
          placeholder="Search by name..."
          variant="outlined"
          size="small"
          fullWidth
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
        />
      </Paper>

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Designation</TableCell>
              <TableCell>Practice group</TableCell>
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
            ) : officers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 5 }}>
                  <Typography color="text.secondary">No lawyers found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              officers.map((officer) => (
                <TableRow key={officer.lawyer_id} hover>
                  <TableCell>{officer.lawyer_id}</TableCell>
                  <TableCell>
                    <Typography variant="body1">
                      {officer.fname} {officer.lname}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={officer.designation || 'N/A'} size="small" color="primary" variant="outlined" />
                  </TableCell>
                  <TableCell>{officer.group_name || 'Unassigned'}</TableCell>
                  <TableCell>
                    <Chip label={officer.total_cases} size="small" color="info" />
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