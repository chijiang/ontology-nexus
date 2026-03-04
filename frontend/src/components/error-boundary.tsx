'use client'

import React, { Component, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="flex items-center justify-center p-8">
          <div className="text-center space-y-3">
            <p className="text-sm text-muted-foreground">
              {this.state.error?.message || 'Component failed to render.'}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              Retry
            </Button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
