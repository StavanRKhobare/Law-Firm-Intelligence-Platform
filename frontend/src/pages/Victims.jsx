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
import { clientsAPI } from '../services/api';

export default function Victims() {
  const [victims, setVictims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchVictims();
  }, [page, rowsPerPage, search]);

  const fetchVictims = async () => {
    try {
      setLoading(true);
      const params = {
        page: page + 1,
        size: rowsPerPage,
        ...(search && { search }),
      };
      const response = await clientsAPI.getAll(params);
      setVictims(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      console.error('Error fetching victims:', error);
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
        Clients
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
        </Box>
      </Paper>

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Notes</TableCell>
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
            ) : victims.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 5 }}>
                  <Typography color="text.secondary">No clients found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              victims.map((victim) => (
                <TableRow key={victim.client_id} hover>
                  <TableCell>{victim.client_id}</TableCell>
                  <TableCell>
                    <Typography variant="body1">
                      {victim.fname} {victim.lname}
                    </Typography>
                  </TableCell>
                  <TableCell>{victim.email || 'N/A'}</TableCell>
                  <TableCell>
                    {victim.notes ? (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" sx={{ maxWidth: 300 }}>
                          {victim.notes}
                        </Typography>
                      </Box>
                    ) : (
                      <Chip label="None" size="small" variant="outlined" />
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip label={victim.total_cases} size="small" color="info" />
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