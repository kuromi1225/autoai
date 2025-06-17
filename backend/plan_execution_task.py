@celery.task
def execute_plan_task(plan_id):
    """計画実行タスク（非同期）"""
    try:
        logger.info(f"Executing plan: {plan_id}")
        
        # 計画の詳細を取得
        from services.plan_reviewer import PlanReviewer
        plan_reviewer = PlanReviewer()
        
        plan = plan_reviewer.get_plan(plan_id)
        if not plan:
            logger.error(f"Plan not found: {plan_id}")
            socketio.emit('plan_execution_failed', {
                'plan_id': plan_id,
                'error': 'Plan not found'
            })
            return
        
        # 計画実行開始の通知
        socketio.emit('plan_execution_started', {
            'plan_id': plan_id,
            'total_steps': len(plan.steps),
            'estimated_time': plan.estimated_total_time
        })
        
        # 各ステップを順次実行
        for i, step in enumerate(plan.steps):
            try:
                # ステップ開始の通知
                socketio.emit('step_started', {
                    'plan_id': plan_id,
                    'step_id': step.id,
                    'step_index': i,
                    'step_title': step.title,
                    'step_description': step.description
                })
                
                # ステップの実行（シミュレーション）
                import time
                execution_time = min(step.estimated_time / 100, 30)  # 最大30秒
                
                # 進捗の更新
                for progress in range(0, 101, 20):
                    time.sleep(execution_time / 5)
                    socketio.emit('step_progress', {
                        'plan_id': plan_id,
                        'step_id': step.id,
                        'progress': progress,
                        'message': f'{step.title} - {progress}%完了'
                    })
                
                # ステップ完了の通知
                socketio.emit('step_completed', {
                    'plan_id': plan_id,
                    'step_id': step.id,
                    'step_index': i,
                    'result': f'{step.title}が正常に完了しました'
                })
                
                # 全体の進捗を更新
                overall_progress = int((i + 1) / len(plan.steps) * 100)
                socketio.emit('plan_progress', {
                    'plan_id': plan_id,
                    'progress': overall_progress,
                    'completed_steps': i + 1,
                    'total_steps': len(plan.steps)
                })
                
            except Exception as step_error:
                logger.error(f"Step execution failed: {step.id}, error: {step_error}")
                
                # ステップ失敗の通知
                socketio.emit('step_failed', {
                    'plan_id': plan_id,
                    'step_id': step.id,
                    'step_index': i,
                    'error': str(step_error)
                })
                
                # 計画全体を失敗として処理
                socketio.emit('plan_execution_failed', {
                    'plan_id': plan_id,
                    'failed_step': step.id,
                    'error': str(step_error)
                })
                return
        
        # 計画完了の通知
        socketio.emit('plan_execution_completed', {
            'plan_id': plan_id,
            'status': 'completed',
            'message': '計画が正常に完了しました',
            'completed_steps': len(plan.steps)
        })
        
        logger.info(f"Plan execution completed: {plan_id}")
        
    except Exception as e:
        logger.error(f"Plan execution failed: {plan_id}, error: {e}")
        
        socketio.emit('plan_execution_failed', {
            'plan_id': plan_id,
            'error': str(e)
        })

