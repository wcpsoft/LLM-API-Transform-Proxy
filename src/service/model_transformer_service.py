from typing import List, Dict, Any, Optional
from src.service.model_service import ModelService
from src.service.api_key_service import ApiKeyService
from src.utils.logging import logger


class ModelTransformerService:
    """模型转换服务 - 统一处理模型路由和转换逻辑"""
    
    @staticmethod
    def find_best_model(source_model: str, enable_transformer: bool = True) -> Optional[Dict[str, Any]]:
        """
        根据源模型名称找到最佳匹配的目标模型
        
        Args:
            source_model: 源模型名称
            enable_transformer: 是否启用transformer模式进行智能转换
            
        Returns:
            匹配的模型配置，如果没有找到则返回None
        """
        logger.info(f"开始路由模型: {source_model}")
        
        # 1. 首先尝试直接匹配路由键
        models = ModelService.get_models_by_route_key(source_model)
        if models:
            logger.info(f"直接路由键匹配成功: {len(models)} 个模型")
            # 检查直接匹配的模型是否有可用密钥
            direct_match_model = models[0]
            provider_keys = ApiKeyService.get_active_keys_by_provider(direct_match_model['provider'])
            if provider_keys:
                logger.info(f"直接匹配模型有可用密钥，使用: {direct_match_model['provider']}")
                return direct_match_model
            else:
                logger.info(f"直接匹配模型 {direct_match_model['provider']} 无可用密钥，进入transformer模式")
        
        logger.info(f"直接路由键匹配结果: 0 个模型")
        
        # 2. 获取所有模型进行智能匹配
        all_models = ModelService.get_all_models()
        logger.info(f"总共有 {len(all_models)} 个模型配置")
        
        # 3. 精确目标模型匹配
        exact_match_model = ModelTransformerService._find_exact_match(source_model, all_models)
        if exact_match_model:
            # 检查精确匹配模型是否有可用密钥
            provider_keys = ApiKeyService.get_active_keys_by_provider(exact_match_model['provider'])
            if provider_keys:
                logger.info(f"精确匹配模型有可用密钥，使用: {exact_match_model['provider']}")
                return exact_match_model
            else:
                logger.info(f"精确匹配模型 {exact_match_model['provider']} 无可用密钥，进入transformer模式")
        
        # 4. 如果启用transformer模式，进行智能转换
        if enable_transformer:
            transformed_model = ModelTransformerService._apply_transformer_logic(source_model, all_models)
            if transformed_model:
                return transformed_model
        
        # 5. 通用匹配逻辑
        general_match = ModelTransformerService._find_general_match(source_model, all_models)
        if general_match:
            return general_match
        
        # 6. 使用默认模型
        logger.warning("未找到匹配模型，使用默认chat模型")
        default_models = ModelService.get_models_by_route_key('chat')
        return default_models[0] if default_models else None
    
    @staticmethod
    def _find_exact_match(source_model: str, all_models: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """查找精确目标模型匹配"""
        for model_config in all_models:
            if model_config['enabled'] and model_config['target_model'] == source_model:
                logger.info(f"找到精确目标模型匹配: {model_config['route_key']} -> {model_config['target_model']}")
                return model_config
        return None
    
    @staticmethod
    def _apply_transformer_logic(source_model: str, all_models: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """应用transformer模式的智能转换逻辑"""
        logger.info("进入transformer模式，开始智能模型转换")
        
        # Claude模型转换逻辑
        if 'claude' in source_model.lower():
            logger.info(f"检测到Claude模型请求: {source_model}，尝试转换到可用服务商")
            # 优先使用DeepSeek
            for model_config in all_models:
                if (model_config['enabled'] and 
                    model_config['provider'] == 'deepseek' and 
                    'deepseek-chat' in model_config['target_model']):
                    logger.info(f"Claude模型转换: {source_model} -> {model_config['target_model']} (DeepSeek)")
                    return model_config
        
        # GPT模型转换逻辑
        elif 'gpt' in source_model.lower():
            logger.info(f"检测到GPT模型请求: {source_model}，尝试转换到可用服务商")
            # 优先使用DeepSeek
            for model_config in all_models:
                if (model_config['enabled'] and 
                    model_config['provider'] == 'deepseek'):
                    logger.info(f"GPT模型转换: {source_model} -> {model_config['target_model']} (DeepSeek)")
                    return model_config
        
        # Gemini模型转换逻辑
        elif 'gemini' in source_model.lower():
            logger.info(f"检测到Gemini模型请求: {source_model}，尝试转换到可用服务商")
            # 优先使用DeepSeek
            for model_config in all_models:
                if (model_config['enabled'] and 
                    model_config['provider'] == 'deepseek'):
                    logger.info(f"Gemini模型转换: {source_model} -> {model_config['target_model']} (DeepSeek)")
                    return model_config
        
        return None
    
    @staticmethod
    def _find_general_match(source_model: str, all_models: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """通用匹配逻辑"""
        for model_config in all_models:
            if model_config['enabled']:
                # 检查提供商名称匹配
                if source_model.startswith(model_config['provider']):
                    logger.info(f"找到提供商匹配: {model_config['provider']}")
                    return model_config
                
                # 检查路由键部分匹配
                if model_config['route_key'] in source_model or source_model in model_config['route_key']:
                    logger.info(f"找到路由键部分匹配: {model_config['route_key']}")
                    return model_config
                
                # 检查关键词匹配（优先级最低）
                keywords = model_config.get('prompt_keywords', '')
                if keywords and any(keyword.strip() in source_model for keyword in keywords.split(',')):
                    logger.info(f"找到关键词匹配: {keywords}")
                    return model_config
        
        return None
    
    @staticmethod
    def get_available_api_key(provider_name: str) -> Optional[Dict[str, Any]]:
        """获取指定提供商的可用API密钥"""
        api_keys = ApiKeyService.get_active_keys_by_provider(provider_name)
        logger.info(f"查询到的{provider_name}密钥数量: {len(api_keys)}")
        
        if not api_keys:
            logger.error(f"没有找到可用的{provider_name}密钥")
            return None
        
        # 简单选择第一个可用密钥（可以后续优化为负载均衡）
        selected_key = api_keys[0]
        logger.info(f"选择的密钥ID: {selected_key['id']}")
        return selected_key