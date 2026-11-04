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
  Chip,
  IconButton,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { Download, AttachFile } from '@mui/icons-material';
import { evidenceAPI } from '../services/api';

const statusColors = {
  'Received': 'info',
  'Under Review': 'warning',
  'Filed': 'default',
  'Produced': 'success',
};

export default function Evidence() {
  const [evidence, setEvidence] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');
  const [hasFileFilter, setHasFileFilter] = useState('');

  useEffect(() => {
    fetchEvidence();
  }, [page, rowsPerPage, statusFilter, hasFileFilter]);

  const fetchEvidence = async () => {
    try {
      setLoading(true);
      const params = {
        page: page + 1,
        size: rowsPerPage,
        ...(statusFilter && { status: statusFilter }),
        ...(hasFileFilter !== '' && { has_file: hasFileFilter === 'true' }),
      };
      const response = await evidenceAPI.getAll(params);
      setEvidence(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      console.error('Error fetching evidence:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (evidenceId) => {
    try {
      const response = await evidenceAPI.downloadFile(evidenceId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `evidence_${evidenceId}.file`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error downloading file:', error);
      alert('Failed to download file');
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
        Evidence
      </Typography>

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="Received">Received</MenuItem>
              <MenuItem value="Under Review">Under Review</MenuItem>
              <MenuItem value="Filed">Filed</MenuItem>
              <MenuItem value="Produced">Produced</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>File Attachment</InputLabel>
            <Select
              value={hasFileFilter}
              label="File Attachment"
              onChange={(e) => setHasFileFilter(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="true">With File</MenuItem>
              <MenuItem value="false">Without File</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Paper>

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Filed date</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Case</TableCell>
              <TableCell>Lawyer</TableCell>
              <TableCell>File</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 5 }}>
                  <CircularProgress />
                </TableCell>
              </TableRow>
            ) : evidence.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 5 }}>
                  <Typography color="text.secondary">No evidence found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              evidence.map((item) => (
                <TableRow key={item.evidence_id} hover>
                  <TableCell>{item.evidence_id}</TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ maxWidth: 300 }}>
                      {item.description || 'N/A'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {new Date(item.filed_date).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={item.status}
                      color={statusColors[item.status]}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{item.case_title || 'N/A'}</TableCell>
                  <TableCell>{item.lawyer_name || 'N/A'}</TableCell>
                  <TableCell>
                    {item.has_file ? (
                      <Tooltip title="Download file">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => handleDownload(item.evidence_id)}
                        >
                          <Download />
                        </IconButton>
                      </Tooltip>
                    ) : (
                      <Chip
                        icon={<AttachFile />}
                        label="No file"
                        size="small"
                        variant="outlined"
                      />
                    )}
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