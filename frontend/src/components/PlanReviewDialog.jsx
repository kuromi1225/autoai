import React from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { 
  Clock, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Shield,
  RotateCcw
} from 'lucide-react'

const PlanReviewDialog = ({ open, onOpenChange, plan, onApprove, onReject }) => {
  if (!plan) return null
  
  const getRiskBadge = (riskLevel) => {
    switch (riskLevel) {
      case 'low':
        return <Badge variant="default" className="bg-green-500"><CheckCircle className="w-3 h-3 mr-1" />低リスク</Badge>
      case 'medium':
        return <Badge variant="default" className="bg-yellow-500"><AlertTriangle className="w-3 h-3 mr-1" />中リスク</Badge>
      case 'high':
        return <Badge variant="destructive"><XCircle className="w-3 h-3 mr-1" />高リスク</Badge>
      default:
        return <Badge variant="outline">不明</Badge>
    }
  }
  
  const getOverallRiskColor = (riskLevel) => {
    switch (riskLevel) {
      case 'low':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'high':
        return 'text-red-600 bg-red-50 border-red-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }
  
  const formatTime = (seconds) => {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    
    if (minutes > 0) {
      return `${minutes}分${remainingSeconds > 0 ? remainingSeconds + '秒' : ''}`
    }
    return `${remainingSeconds}秒`
  }
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Shield className="w-5 h-5" />
            <span>実行計画の確認</span>
          </DialogTitle>
          <DialogDescription>
            以下の計画を実行する前に、内容とリスクを確認してください。
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* 計画概要 */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">{plan.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-700 mb-4">{plan.description}</p>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-600">
                    予想実行時間: <strong>{formatTime(plan.estimated_total_time)}</strong>
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">
                    ステップ数: <strong>{plan.steps.length}</strong>
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
          
          {/* リスク評価 */}
          <Card className={`border-2 ${getOverallRiskColor(plan.risk_assessment.overall_risk)}`}>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4" />
                <span>リスク評価</span>
                {getRiskBadge(plan.risk_assessment.overall_risk)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">
                    {plan.risk_assessment.high_risk_steps}
                  </div>
                  <div className="text-gray-600">高リスクステップ</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-yellow-600">
                    {plan.risk_assessment.medium_risk_steps}
                  </div>
                  <div className="text-gray-600">中リスクステップ</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">
                    {plan.risk_assessment.irreversible_steps}
                  </div>
                  <div className="text-gray-600">不可逆ステップ</div>
                </div>
              </div>
            </CardContent>
          </Card>
          
          {/* 実行ステップ */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">実行ステップ</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-64 px-6">
                <div className="space-y-3 pb-4">
                  {plan.steps.map((step, index) => (
                    <div key={step.id} className="border rounded-lg p-3">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          <div className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium">
                            {index + 1}
                          </div>
                          <h4 className="font-medium text-gray-900">{step.title}</h4>
                        </div>
                        <div className="flex items-center space-x-2">
                          {getRiskBadge(step.risk_level)}
                          {!step.reversible && (
                            <Badge variant="outline" className="text-orange-600 border-orange-300">
                              <RotateCcw className="w-3 h-3 mr-1" />
                              不可逆
                            </Badge>
                          )}
                        </div>
                      </div>
                      
                      <p className="text-sm text-gray-600 mb-2">{step.description}</p>
                      
                      <div className="flex items-center space-x-4 text-xs text-gray-500">
                        <span>予想時間: {formatTime(step.estimated_time)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
          
          {/* 警告メッセージ */}
          {(plan.risk_assessment.overall_risk === 'high' || plan.risk_assessment.irreversible_steps > 0) && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start space-x-2">
                <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-red-800 mb-1">重要な注意事項</p>
                  <ul className="text-red-700 space-y-1">
                    {plan.risk_assessment.overall_risk === 'high' && (
                      <li>• この計画には高リスクな操作が含まれています</li>
                    )}
                    {plan.risk_assessment.irreversible_steps > 0 && (
                      <li>• 一部のステップは実行後に元に戻すことができません</li>
                    )}
                    <li>• 実行前にバックアップを取ることを強く推奨します</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
        
        <Separator />
        
        <DialogFooter className="flex justify-between">
          <Button variant="outline" onClick={onReject}>
            <XCircle className="w-4 h-4 mr-2" />
            拒否
          </Button>
          <Button onClick={onApprove} className="bg-blue-600 hover:bg-blue-700">
            <CheckCircle className="w-4 h-4 mr-2" />
            承認して実行
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default PlanReviewDialog

