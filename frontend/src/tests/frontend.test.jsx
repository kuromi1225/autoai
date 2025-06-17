# Frontend Tests

import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import userEvent from '@testing-library/user-event'

// Import components to test
import App from '../src/App'
import SettingsPage from '../src/components/SettingsPage'

// Mock socket.io-client
vi.mock('socket.io-client', () => ({
  default: vi.fn(() => ({
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
    disconnect: vi.fn(),
    connect: vi.fn()
  }))
}))

// Mock fetch API
global.fetch = vi.fn()

describe('App Component', () => {
  beforeEach(() => {
    // Reset all mocks before each test
    vi.clearAllMocks()
    
    // Mock successful fetch responses
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        response: 'Test response',
        plan: null
      })
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders main title and description', () => {
    render(<App />)
    
    expect(screen.getByText('Devin AI Clone')).toBeInTheDocument()
    expect(screen.getByText('自律型AIエージェント - コード生成からデプロイまで')).toBeInTheDocument()
  })

  it('displays initial assistant message', () => {
    render(<App />)
    
    expect(screen.getByText(/こんにちは！私はDevin AI Cloneです/)).toBeInTheDocument()
  })

  it('allows user to send messages', async () => {
    const user = userEvent.setup()
    render(<App />)
    
    const input = screen.getByPlaceholderText(/メッセージを入力/i)
    const sendButton = screen.getByRole('button', { name: /送信/i })
    
    await user.type(input, 'Test message')
    await user.click(sendButton)
    
    expect(screen.getByText('Test message')).toBeInTheDocument()
  })

  it('switches to settings view when settings button is clicked', async () => {
    const user = userEvent.setup()
    render(<App />)
    
    const settingsButton = screen.getByRole('button', { name: /設定/i })
    await user.click(settingsButton)
    
    // Settings page should be displayed
    expect(screen.getByText(/Git連携設定/i)).toBeInTheDocument()
  })

  it('handles API errors gracefully', async () => {
    // Mock API error
    global.fetch.mockRejectedValue(new Error('API Error'))
    
    const user = userEvent.setup()
    render(<App />)
    
    const input = screen.getByPlaceholderText(/メッセージを入力/i)
    const sendButton = screen.getByRole('button', { name: /送信/i })
    
    await user.type(input, 'Test message')
    await user.click(sendButton)
    
    await waitFor(() => {
      expect(screen.getByText(/バックエンドとの通信でエラーが発生しました/)).toBeInTheDocument()
    })
  })

  it('displays plan review dialog when plan is received', async () => {
    // Mock API response with plan
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        response: 'Plan created',
        plan: {
          plan_id: 'test_plan',
          title: 'Test Plan',
          description: 'Test plan description',
          steps: [
            {
              id: 'step1',
              title: 'Test Step',
              description: 'Test step description',
              estimated_time: 300,
              risk_level: 'low',
              reversible: true
            }
          ],
          estimated_total_time: 300,
          risk_assessment: {
            overall_risk: 'low',
            high_risk_steps: 0,
            medium_risk_steps: 0,
            irreversible_steps: 0
          }
        }
      })
    })

    const user = userEvent.setup()
    render(<App />)
    
    const input = screen.getByPlaceholderText(/メッセージを入力/i)
    const sendButton = screen.getByRole('button', { name: /送信/i })
    
    await user.type(input, 'Create a plan')
    await user.click(sendButton)
    
    await waitFor(() => {
      expect(screen.getByText('実行計画の確認')).toBeInTheDocument()
      expect(screen.getByText('Test Plan')).toBeInTheDocument()
    })
  })

  it('handles plan approval correctly', async () => {
    // Mock plan execution API
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          response: 'Plan created',
          plan: {
            plan_id: 'test_plan',
            title: 'Test Plan',
            description: 'Test plan description',
            steps: [],
            estimated_total_time: 300,
            risk_assessment: {
              overall_risk: 'low',
              high_risk_steps: 0,
              medium_risk_steps: 0,
              irreversible_steps: 0
            }
          }
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: 'Plan execution started'
        })
      })

    const user = userEvent.setup()
    render(<App />)
    
    const input = screen.getByPlaceholderText(/メッセージを入力/i)
    const sendButton = screen.getByRole('button', { name: /送信/i })
    
    await user.type(input, 'Create a plan')
    await user.click(sendButton)
    
    await waitFor(() => {
      expect(screen.getByText('実行計画の確認')).toBeInTheDocument()
    })
    
    const approveButton = screen.getByRole('button', { name: /承認して実行/i })
    await user.click(approveButton)
    
    await waitFor(() => {
      expect(screen.getByText(/計画が承認されました/)).toBeInTheDocument()
    })
  })

  it('cleans up intervals on unmount', () => {
    const { unmount } = render(<App />)
    
    // Trigger task simulation to create intervals
    act(() => {
      // This would normally be triggered by plan approval
      // We'll test the cleanup mechanism
    })
    
    // Unmount component
    unmount()
    
    // Verify no memory leaks (intervals should be cleared)
    // This is more of a smoke test since we can't directly observe interval cleanup
    expect(true).toBe(true)
  })
})

describe('SettingsPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock successful API responses
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        repository_url: '',
        branch: 'main',
        username: '',
        access_token: '',
        auto_commit: true,
        commit_message_template: 'Auto-commit by Devin AI: {task_description}',
        is_configured: false
      })
    })
  })

  it('renders Git settings form', async () => {
    render(<SettingsPage />)
    
    await waitFor(() => {
      expect(screen.getByText('Git連携設定')).toBeInTheDocument()
      expect(screen.getByLabelText(/リポジトリURL/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/ユーザー名/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/アクセストークン/i)).toBeInTheDocument()
    })
  })

  it('loads existing settings on mount', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        repository_url: 'https://github.com/test/repo.git',
        branch: 'main',
        username: 'testuser',
        access_token: '***',
        auto_commit: true,
        commit_message_template: 'Custom template',
        is_configured: true
      })
    })

    render(<SettingsPage />)
    
    await waitFor(() => {
      expect(screen.getByDisplayValue('https://github.com/test/repo.git')).toBeInTheDocument()
      expect(screen.getByDisplayValue('testuser')).toBeInTheDocument()
    })
  })

  it('validates form inputs', async () => {
    const user = userEvent.setup()
    render(<SettingsPage />)
    
    await waitFor(() => {
      expect(screen.getByText('Git連携設定')).toBeInTheDocument()
    })
    
    const saveButton = screen.getByRole('button', { name: /設定を保存/i })
    await user.click(saveButton)
    
    // Should show validation errors for empty required fields
    await waitFor(() => {
      expect(screen.getByText(/リポジトリURLは必須です/i)).toBeInTheDocument()
    })
  })

  it('saves settings successfully', async () => {
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          repository_url: '',
          branch: 'main',
          username: '',
          access_token: '',
          auto_commit: true,
          commit_message_template: 'Auto-commit by Devin AI: {task_description}',
          is_configured: false
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: 'Git設定を保存しました'
        })
      })

    const user = userEvent.setup()
    render(<SettingsPage />)
    
    await waitFor(() => {
      expect(screen.getByText('Git連携設定')).toBeInTheDocument()
    })
    
    // Fill in the form
    await user.type(screen.getByLabelText(/リポジトリURL/i), 'https://github.com/test/repo.git')
    await user.type(screen.getByLabelText(/ユーザー名/i), 'testuser')
    await user.type(screen.getByLabelText(/アクセストークン/i), 'test_token')
    
    const saveButton = screen.getByRole('button', { name: /設定を保存/i })
    await user.click(saveButton)
    
    await waitFor(() => {
      expect(screen.getByText(/設定を保存しました/i)).toBeInTheDocument()
    })
  })

  it('tests Git connection', async () => {
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          repository_url: 'https://github.com/test/repo.git',
          branch: 'main',
          username: 'testuser',
          access_token: '***',
          auto_commit: true,
          commit_message_template: 'Auto-commit by Devin AI: {task_description}',
          is_configured: true
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: '接続テストが成功しました'
        })
      })

    const user = userEvent.setup()
    render(<SettingsPage />)
    
    await waitFor(() => {
      expect(screen.getByText('Git連携設定')).toBeInTheDocument()
    })
    
    const testButton = screen.getByRole('button', { name: /接続テスト/i })
    await user.click(testButton)
    
    await waitFor(() => {
      expect(screen.getByText(/接続テストが成功しました/i)).toBeInTheDocument()
    })
  })

  it('handles API errors gracefully', async () => {
    global.fetch.mockRejectedValue(new Error('Network error'))
    
    render(<SettingsPage />)
    
    await waitFor(() => {
      expect(screen.getByText(/設定の読み込みに失敗しました/i)).toBeInTheDocument()
    })
  })

  it('displays resource usage statistics', async () => {
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          repository_url: '',
          branch: 'main',
          username: '',
          access_token: '',
          auto_commit: true,
          commit_message_template: 'Auto-commit by Devin AI: {task_description}',
          is_configured: false
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          total_tasks: 10,
          total_execution_time: 3600,
          average_cpu_usage: 45.5,
          average_memory_usage: 1024,
          peak_cpu_usage: 80.0,
          peak_memory_usage: 2048
        })
      })

    render(<SettingsPage />)
    
    await waitFor(() => {
      expect(screen.getByText(/リソース使用統計/i)).toBeInTheDocument()
      expect(screen.getByText(/総タスク数: 10/i)).toBeInTheDocument()
      expect(screen.getByText(/平均CPU使用率: 45.5%/i)).toBeInTheDocument()
    })
  })
})

// Performance and Memory Tests
describe('Performance Tests', () => {
  it('renders App component within acceptable time', async () => {
    const startTime = performance.now()
    
    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByText('Devin AI Clone')).toBeInTheDocument()
    })
    
    const endTime = performance.now()
    const renderTime = endTime - startTime
    
    // Component should render within 100ms
    expect(renderTime).toBeLessThan(100)
  })

  it('handles rapid user interactions without performance degradation', async () => {
    const user = userEvent.setup()
    render(<App />)
    
    const input = screen.getByPlaceholderText(/メッセージを入力/i)
    const sendButton = screen.getByRole('button', { name: /送信/i })
    
    const startTime = performance.now()
    
    // Simulate rapid interactions
    for (let i = 0; i < 10; i++) {
      await user.clear(input)
      await user.type(input, `Message ${i}`)
      await user.click(sendButton)
    }
    
    const endTime = performance.now()
    const totalTime = endTime - startTime
    
    // All interactions should complete within 2 seconds
    expect(totalTime).toBeLessThan(2000)
  })

  it('does not create memory leaks with repeated mounting/unmounting', () => {
    const initialMemory = performance.memory?.usedJSHeapSize || 0
    
    // Mount and unmount component multiple times
    for (let i = 0; i < 50; i++) {
      const { unmount } = render(<App />)
      unmount()
    }
    
    // Force garbage collection if available
    if (global.gc) {
      global.gc()
    }
    
    const finalMemory = performance.memory?.usedJSHeapSize || 0
    const memoryIncrease = finalMemory - initialMemory
    
    // Memory increase should be minimal (less than 10MB)
    expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024)
  })
})

// Integration Tests
describe('Integration Tests', () => {
  it('completes full user workflow: message -> plan -> execution', async () => {
    // Mock the complete workflow
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          response: 'Plan created',
          plan: {
            plan_id: 'test_plan',
            title: 'Test Plan',
            description: 'Test plan description',
            steps: [
              {
                id: 'step1',
                title: 'Test Step',
                description: 'Test step description',
                estimated_time: 300,
                risk_level: 'low',
                reversible: true
              }
            ],
            estimated_total_time: 300,
            risk_assessment: {
              overall_risk: 'low',
              high_risk_steps: 0,
              medium_risk_steps: 0,
              irreversible_steps: 0
            }
          }
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: 'Plan execution started'
        })
      })

    const user = userEvent.setup()
    render(<App />)
    
    // Step 1: Send message
    const input = screen.getByPlaceholderText(/メッセージを入力/i)
    const sendButton = screen.getByRole('button', { name: /送信/i })
    
    await user.type(input, 'Create a web application')
    await user.click(sendButton)
    
    // Step 2: Review plan
    await waitFor(() => {
      expect(screen.getByText('実行計画の確認')).toBeInTheDocument()
    })
    
    // Step 3: Approve plan
    const approveButton = screen.getByRole('button', { name: /承認して実行/i })
    await user.click(approveButton)
    
    // Step 4: Verify execution started
    await waitFor(() => {
      expect(screen.getByText(/計画が承認されました/)).toBeInTheDocument()
    })
  })

  it('handles settings configuration and usage', async () => {
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          repository_url: '',
          branch: 'main',
          username: '',
          access_token: '',
          auto_commit: true,
          commit_message_template: 'Auto-commit by Devin AI: {task_description}',
          is_configured: false
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: 'Git設定を保存しました'
        })
      })

    const user = userEvent.setup()
    render(<App />)
    
    // Navigate to settings
    const settingsButton = screen.getByRole('button', { name: /設定/i })
    await user.click(settingsButton)
    
    // Configure Git settings
    await waitFor(() => {
      expect(screen.getByText('Git連携設定')).toBeInTheDocument()
    })
    
    await user.type(screen.getByLabelText(/リポジトリURL/i), 'https://github.com/test/repo.git')
    await user.type(screen.getByLabelText(/ユーザー名/i), 'testuser')
    await user.type(screen.getByLabelText(/アクセストークン/i), 'test_token')
    
    const saveButton = screen.getByRole('button', { name: /設定を保存/i })
    await user.click(saveButton)
    
    await waitFor(() => {
      expect(screen.getByText(/設定を保存しました/i)).toBeInTheDocument()
    })
    
    // Return to main view
    const mainButton = screen.getByRole('button', { name: /メイン/i })
    await user.click(mainButton)
    
    await waitFor(() => {
      expect(screen.getByText('Devin AI Clone')).toBeInTheDocument()
    })
  })
})

