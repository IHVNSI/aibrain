import React, { useState, useEffect } from 'react'
import api from '../api/client'
import {
  Clock, Plus, Trash2, CheckCircle2, XCircle, Loader, Edit2,
  RefreshCw, AlertCircle, Power, Zap, List, Calendar
} from 'lucide-react'
import Swal from 'sweetalert2'

export default function SchedulerTab() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [schedulerRunning, setSchedulerRunning] = useState(false)
  const [lastRefresh, setLastRefresh] = useState(null)

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    task_type: 'email_check',
    instruction: '',
    description: '',
    task_config: {}
  })

  // Load tasks on mount
  useEffect(() => {
    loadTasks()
  }, [])

  const loadTasks = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/api/scheduler/tasks')
      if (data.success) {
        setTasks(data.tasks || [])
        setLastRefresh(new Date().toLocaleTimeString())
        setMsg({ type: 'success', text: `Loaded ${data.tasks.length} task(s)` })
        setTimeout(() => setMsg(null), 2000)
      }
    } catch (error) {
      console.error('Error loading tasks:', error)
      setMsg({ type: 'error', text: 'Failed to load tasks' })
    } finally {
      setLoading(false)
    }
  }

  const createTask = async (e) => {
    e.preventDefault()
    if (!formData.name.trim() || !formData.instruction.trim()) {
      setMsg({ type: 'error', text: 'Name and instruction are required' })
      return
    }

    setLoading(true)
    try {
      const { data } = await api.post('/api/scheduler/tasks', formData)
      if (data.success) {
        setMsg({ type: 'success', text: `Task '${formData.name}' created successfully` })
        setFormData({ name: '', task_type: 'email_check', instruction: '', description: '', task_config: {} })
        setShowCreateForm(false)
        await loadTasks()
      } else {
        setMsg({ type: 'error', text: data.error || 'Failed to create task' })
      }
    } catch (error) {
      console.error('Error creating task:', error)
      setMsg({ type: 'error', text: error.response?.data?.error || 'Failed to create task' })
    } finally {
      setLoading(false)
    }
  }

  const updateTask = async (e) => {
    e.preventDefault()
    if (!editingTask.name.trim() || !editingTask.instruction.trim()) {
      setMsg({ type: 'error', text: 'Name and instruction are required' })
      return
    }

    setLoading(true)
    try {
      const { data } = await api.put(`/api/scheduler/tasks/${editingTask.id}`, {
        name: editingTask.name,
        instruction: editingTask.instruction,
        description: editingTask.description,
        is_active: editingTask.is_active
      })
      if (data.success) {
        setMsg({ type: 'success', text: 'Task updated successfully' })
        setEditingTask(null)
        await loadTasks()
      }
    } catch (error) {
      console.error('Error updating task:', error)
      setMsg({ type: 'error', text: 'Failed to update task' })
    } finally {
      setLoading(false)
    }
  }

  const deleteTask = async (taskId, taskName) => {
    const result = await Swal.fire({
      title: 'Delete Task',
      text: `Are you sure you want to delete "${taskName}"?`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Delete',
      confirmButtonColor: '#dc2626',
      cancelButtonText: 'Cancel'
    })

    if (result.isConfirmed) {
      try {
        const { data } = await api.delete(`/api/scheduler/tasks/${taskId}`)
        if (data.success) {
          setMsg({ type: 'success', text: 'Task deleted successfully' })
          await loadTasks()
        }
      } catch (error) {
        console.error('Error deleting task:', error)
        setMsg({ type: 'error', text: 'Failed to delete task' })
      }
    }
  }

  const toggleTask = async (task) => {
    const endpoint = task.is_active ? 'disable' : 'enable'
    try {
      const { data } = await api.post(`/api/scheduler/tasks/${task.id}/${endpoint}`)
      if (data.success) {
        setMsg({ type: 'success', text: `Task ${endpoint}d successfully` })
        await loadTasks()
      }
    } catch (error) {
      console.error(`Error ${endpoint}ing task:`, error)
      setMsg({ type: 'error', text: `Failed to ${endpoint} task` })
    }
  }

  const startScheduler = async () => {
    try {
      const { data } = await api.post('/api/scheduler/start')
      if (data.success) {
        setSchedulerRunning(true)
        setMsg({ type: 'success', text: 'Scheduler started successfully' })
        setTimeout(() => setMsg(null), 2000)
      }
    } catch (error) {
      console.error('Error starting scheduler:', error)
      setMsg({ type: 'error', text: 'Failed to start scheduler' })
    }
  }

  const stopScheduler = async () => {
    const result = await Swal.fire({
      title: 'Stop Scheduler',
      text: 'Are you sure? Tasks will not run while scheduler is stopped.',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Stop',
      cancelButtonText: 'Cancel'
    })

    if (result.isConfirmed) {
      try {
        const { data } = await api.post('/api/scheduler/stop')
        if (data.success) {
          setSchedulerRunning(false)
          setMsg({ type: 'success', text: 'Scheduler stopped' })
        }
      } catch (error) {
        console.error('Error stopping scheduler:', error)
        setMsg({ type: 'error', text: 'Failed to stop scheduler' })
      }
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Clock size={28} className="text-purple-600" />
          Task Scheduler
        </h2>
        <div className="flex gap-2">
          <button
            onClick={loadTasks}
            disabled={loading}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Messages */}
      {msg && (
        <div className={`p-3 rounded-lg text-sm flex items-center gap-2 ${
          msg.type === 'success'
            ? 'bg-green-50 text-green-700 border border-green-200'
            : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {msg.type === 'success' ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
          {msg.text}
        </div>
      )}

      {/* Scheduler Status and Controls */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${schedulerRunning ? 'bg-green-600' : 'bg-gray-300'}`}></div>
            <div>
              <p className="text-sm font-semibold text-gray-900">
                Scheduler Status: <span className={schedulerRunning ? 'text-green-600' : 'text-gray-600'}>
                  {schedulerRunning ? 'Running' : 'Stopped'}
                </span>
              </p>
              {lastRefresh && (
                <p className="text-xs text-gray-500">Last refreshed: {lastRefresh}</p>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            {!schedulerRunning ? (
              <button
                onClick={startScheduler}
                className="btn-primary flex items-center gap-2"
              >
                <Power size={16} /> Start Scheduler
              </button>
            ) : (
              <button
                onClick={stopScheduler}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium flex items-center gap-2 text-sm"
              >
                <Power size={16} /> Stop Scheduler
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Create Task Form */}
      {showCreateForm && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
          <h3 className="font-semibold text-blue-900 flex items-center gap-2">
            <Plus size={18} /> Create New Task
          </h3>
          <form onSubmit={createTask} className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Task Name *</label>
                <input
                  type="text"
                  placeholder="e.g., Morning Email Check"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Task Type</label>
                <select
                  value={formData.task_type}
                  onChange={(e) => setFormData({ ...formData, task_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                >
                  <option value="email_check">Email Check</option>
                  <option value="email_respond">Email Auto-Response</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Schedule Instruction * <span className="text-xs text-gray-500">(e.g., "at 10 AM" or "every 30 minutes")</span>
                </label>
                <input
                  type="text"
                  placeholder='e.g., "at 10 AM" or "every 30 minutes" or "at 9 AM on Monday"'
                  value={formData.instruction}
                  onChange={(e) => setFormData({ ...formData, instruction: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
                <p className="text-xs text-gray-600 mt-1">
                  Examples: "at 10 AM", "every 30 minutes", "at 9 AM on Monday"
                </p>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  placeholder="Optional description of what this task does"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows="2"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>
            </div>

            <div className="flex gap-2 justify-end">
              <button
                type="button"
                onClick={() => {
                  setShowCreateForm(false)
                  setFormData({ name: '', task_type: 'email_check', instruction: '', description: '', task_config: {} })
                }}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg font-medium hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="btn-primary flex items-center gap-2"
              >
                {loading ? <Loader size={16} className="animate-spin" /> : <Zap size={16} />}
                Create Task
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Create Task Button */}
      {!showCreateForm && (
        <button
          onClick={() => setShowCreateForm(true)}
          className="w-full btn-primary flex items-center justify-center gap-2"
        >
          <Plus size={18} /> Create New Task
        </button>
      )}

      {/* Tasks List */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {loading && (
          <div className="flex justify-center items-center py-12">
            <Loader size={32} className="animate-spin text-purple-600" />
          </div>
        )}

        {!loading && tasks.length === 0 && (
          <div className="text-center py-12">
            <Calendar size={48} className="text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">No tasks scheduled yet</p>
            <p className="text-sm text-gray-400 mt-1">Create one to get started</p>
          </div>
        )}

        {!loading && tasks.length > 0 && (
          <div className="divide-y divide-gray-200">
            {tasks.map((task) => (
              <div
                key={task.id}
                className={`p-4 transition ${
                  !task.is_active ? 'bg-gray-50 opacity-75' : 'hover:bg-gray-50'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    {editingTask?.id === task.id ? (
                      // Edit Mode
                      <form onSubmit={updateTask} className="space-y-3">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Task Name</label>
                          <input
                            type="text"
                            value={editingTask.name}
                            onChange={(e) => setEditingTask({ ...editingTask, name: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Schedule Instruction</label>
                          <input
                            type="text"
                            value={editingTask.instruction}
                            onChange={(e) => setEditingTask({ ...editingTask, instruction: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                          />
                        </div>
                        <div className="flex gap-2">
                          <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2 text-sm">
                            Save
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingTask(null)}
                            className="px-3 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg font-medium text-sm"
                          >
                            Cancel
                          </button>
                        </div>
                      </form>
                    ) : (
                      // View Mode
                      <>
                        <div className="flex items-center gap-2 mb-2">
                          {task.is_active ? (
                            <span className="w-2 h-2 bg-green-600 rounded-full"></span>
                          ) : (
                            <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
                          )}
                          <h3 className="font-semibold text-gray-900">{task.name}</h3>
                          <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                            {task.task_type}
                          </span>
                          {!task.is_active && (
                            <span className="text-xs bg-gray-200 text-gray-700 px-2 py-0.5 rounded">
                              Disabled
                            </span>
                          )}
                        </div>

                        <p className="text-sm text-gray-700 mb-2">
                          <span className="font-medium">📋 Schedule:</span> {task.natural_language_instruction}
                        </p>

                        {task.description && (
                          <p className="text-sm text-gray-600 mb-2">{task.description}</p>
                        )}

                        <div className="grid grid-cols-2 gap-4 text-xs">
                          <div>
                            <p className="text-gray-500">Last Run</p>
                            <p className="text-gray-800 font-medium">
                              {task.last_run ? new Date(task.last_run).toLocaleString() : 'Never'}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500">Next Run</p>
                            <p className="text-gray-800 font-medium">
                              {task.next_run ? new Date(task.next_run).toLocaleString() : 'Not scheduled'}
                            </p>
                          </div>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Action Buttons */}
                  {editingTask?.id !== task.id && (
                    <div className="flex gap-2 flex-shrink-0">
                      <button
                        onClick={() => toggleTask(task)}
                        className={`p-2 rounded hover:bg-gray-200 transition ${
                          task.is_active ? 'text-green-600' : 'text-gray-400'
                        }`}
                        title={task.is_active ? 'Disable task' : 'Enable task'}
                      >
                        <Power size={18} />
                      </button>

                      <button
                        onClick={() => setEditingTask(task)}
                        className="p-2 text-blue-600 rounded hover:bg-gray-200 transition"
                        title="Edit task"
                      >
                        <Edit2 size={18} />
                      </button>

                      <button
                        onClick={() => deleteTask(task.id, task.name)}
                        className="p-2 text-red-600 rounded hover:bg-gray-200 transition"
                        title="Delete task"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
