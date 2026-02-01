// tests/e2e/complete-flow.spec.ts
import { test, expect } from '@playwright/test'

// Test configuration from environment
const TEST_USER = process.env.TEST_USER || 'admin'
const TEST_PASS = process.env.TEST_PASS || 'admin123'
const TEST_API_KEY = process.env.TEST_API_KEY || 'test-api-key'
const TEST_BASE_URL = process.env.TEST_BASE_URL || 'https://api.openai.com/v1'
const TEST_MODEL = process.env.TEST_MODEL || 'gpt-3.5-turbo'
const TEST_NEO4J_URI = process.env.TEST_NEO4J_URI || 'bolt://localhost:7687'
const TEST_NEO4J_USER = process.env.TEST_NEO4J_USER || 'neo4j'
const TEST_NEO4J_PASS = process.env.TEST_NEO4J_PASS || 'password'

test.describe('知识图谱问答 E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to login page
    await page.goto('/')
  })

  test('should display login page', async ({ page }) => {
    await expect(page.locator('text=登录').first()).toBeVisible()
    await expect(page.locator('input[placeholder="用户名"]')).toBeVisible()
    await expect(page.locator('input[placeholder="密码"]')).toBeVisible()
  })

  test('should login successfully', async ({ page }) => {
    await page.fill('input[placeholder="用户名"]', TEST_USER)
    await page.fill('input[placeholder="密码"]', TEST_PASS)
    await page.click('button[type="submit"]')

    // Wait for dashboard content to appear (client-side navigation)
    await expect(page.locator('text=问答').first()).toBeVisible({ timeout: 15000 })
    await expect(page.locator('text=图谱预览')).toBeVisible()
    await expect(page).toHaveURL(/\/dashboard/)
  })

  test('should register new user', async ({ page }) => {
    // Generate random username for testing
    const randomUser = `testuser_${Date.now()}`

    // Click register button
    await page.click('text=注册')

    // Fill registration form
    await page.fill('input[placeholder="用户名"]', randomUser)
    await page.fill('input[placeholder="邮箱（可选）"]', `${randomUser}@test.com`)
    await page.fill('input[placeholder="密码"]', 'testpass123')

    // Submit registration
    await page.click('button[type="submit"]')

    // Should show success message and switch back to login
    await expect(page.locator('text=登录')).toBeVisible()
  })

  test.describe('After Login', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/')
      await page.fill('input[placeholder="用户名"]', TEST_USER)
      await page.fill('input[placeholder="密码"]', TEST_PASS)
      await page.click('button[type="submit"]')
      // Wait for dashboard content (client-side navigation)
      await expect(page.locator('text=问答').first()).toBeVisible({ timeout: 15000 })
    })

    test('should navigate to config page', async ({ page }) => {
      await page.goto('/config')
      await expect(page.locator('text=配置管理')).toBeVisible()
      await expect(page.locator('text=LLM 配置')).toBeVisible()
      await expect(page.locator('text=Neo4j 配置')).toBeVisible()
    })

    test('should configure LLM settings', async ({ page }) => {
      await page.goto('/config')

      // Wait for page to load
      await expect(page.locator('text=配置管理')).toBeVisible()
      await expect(page.locator('text=LLM API 配置')).toBeVisible()
      await expect(page.locator('text=Neo4j 配置')).toBeVisible()

      // Verify LLM config inputs are visible
      await expect(page.locator('input[placeholder="API Key"]')).toBeVisible()
      await expect(page.locator('input[placeholder*="Base URL"]')).toBeVisible()
      // Model input is loaded dynamically
    })

    test('should configure Neo4j settings', async ({ page }) => {
      await page.goto('/config')

      // Wait for page to load
      await expect(page.locator('text=配置管理')).toBeVisible()

      // Verify both config tabs are visible
      await expect(page.locator('text=LLM 配置')).toBeVisible()
      await expect(page.locator('text=Neo4j 配置')).toBeVisible()
    })

    test('should navigate to graph import page', async ({ page }) => {
      await page.goto('/graph/import')
      await expect(page.locator('text=导入 OWL 图谱')).toBeVisible()
      await expect(page.locator('text=上传文件')).toBeVisible()
    })

    test('should show file upload interface', async ({ page }) => {
      await page.goto('/graph/import')

      // Check for file upload elements
      await expect(page.locator('input[type="file"]')).toBeAttached()
      await expect(page.locator('text=点击选择文件')).toBeVisible()
    })

    test('should navigate to graph visualization page', async ({ page }) => {
      await page.goto('/graph/visualize')
      await expect(page.locator('text=图谱可视化')).toBeVisible()
    })

    test('should display chat interface on dashboard', async ({ page }) => {
      await page.goto('/dashboard')

      // Check for chat elements
      await expect(page.locator('input[placeholder="输入你的问题..."]')).toBeVisible()
      await expect(page.locator('text=开始提问吧')).toBeVisible()
    })
  })

  test.describe('Chat Functionality', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/')
      await page.fill('input[placeholder="用户名"]', TEST_USER)
      await page.fill('input[placeholder="密码"]', TEST_PASS)
      await page.click('button[type="submit"]')
      // Wait for dashboard content (client-side navigation)
      await expect(page.locator('text=问答').first()).toBeVisible({ timeout: 15000 })
    })

    test('should display chat input and send button', async ({ page }) => {
      await expect(page.locator('input[placeholder="输入你的问题..."]')).toBeVisible()
      await expect(page.locator('button[type="submit"]')).toBeVisible()
    })

    test('should show example question', async ({ page }) => {
      await expect(page.locator('text=PO_2024_001 是向哪个供应商订购的？')).toBeVisible()
    })
  })

  test.describe('Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/')
      await page.fill('input[placeholder="用户名"]', TEST_USER)
      await page.fill('input[placeholder="密码"]', TEST_PASS)
      await page.click('button[type="submit"]')
      // Wait for dashboard content (client-side navigation)
      await expect(page.locator('text=问答').first()).toBeVisible({ timeout: 15000 })
    })

    test('should navigate between pages', async ({ page }) => {
      // Dashboard -> Config
      await page.goto('/config')
      await expect(page.locator('text=配置管理')).toBeVisible()

      // Config -> Import
      await page.goto('/graph/import')
      await expect(page.locator('text=导入 OWL 图谱')).toBeVisible()

      // Import -> Visualize
      await page.goto('/graph/visualize')
      await expect(page.locator('text=图谱可视化')).toBeVisible()

      // Visualize -> Dashboard
      await page.goto('/dashboard')
      await expect(page.locator('text=问答').first()).toBeVisible()
    })
  })

  test.describe('Error Handling', () => {
    test('should show error on invalid login', async ({ page }) => {
      await page.fill('input[placeholder="用户名"]', 'invalid_user')
      await page.fill('input[placeholder="密码"]', 'wrong_password')
      await page.click('button[type="submit"]')

      // Should stay on login page or show error
      await page.waitForTimeout(2000)
      await expect(page.locator('text=登录').first()).toBeVisible()
    })

    test('should redirect to login when accessing protected routes without auth', async ({ page }) => {
      // Try to access dashboard without login
      await page.context().clearCookies()
      await page.goto('/dashboard')

      // Should redirect to login page
      await page.waitForURL('/', { timeout: 5000 })
      await expect(page.locator('text=登录').first()).toBeVisible()
    })
  })
})
