"""
WhisperFlow Desktop - Test GPU
Script de validation de la configuration CUDA/GPU
"""

import sys
from colorama import init, Fore, Style

init()  # Initialise colorama pour Windows


def print_header(text: str):
    """Affiche un en-tête formaté"""
    print(f"\n{Fore.CYAN}{'='*50}")
    print(f"  {text}")
    print(f"{'='*50}{Style.RESET_ALL}\n")


def print_success(text: str):
    """Affiche un message de succès"""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")


def print_error(text: str):
    """Affiche un message d'erreur"""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")


def print_info(text: str):
    """Affiche une information"""
    print(f"{Fore.YELLOW}→ {text}{Style.RESET_ALL}")


def test_pytorch():
    """Test l'installation de PyTorch"""
    print_header("Test PyTorch")
    
    try:
        import torch
        print_success(f"PyTorch version: {torch.__version__}")
        return True
    except ImportError as e:
        print_error(f"PyTorch non installé: {e}")
        return False


def test_cuda():
    """Test la disponibilité de CUDA"""
    print_header("Test CUDA")
    
    import torch
    
    if torch.cuda.is_available():
        print_success("CUDA est disponible!")
        print_info(f"Version CUDA: {torch.version.cuda}")
        print_info(f"Nombre de GPU: {torch.cuda.device_count()}")
        
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            print_info(f"GPU {i}: {props.name}")
            print_info(f"  - Mémoire totale: {props.total_memory / 1024**3:.1f} GB")
            print_info(f"  - Compute Capability: {props.major}.{props.minor}")
        
        return True
    else:
        print_error("CUDA n'est pas disponible!")
        print_info("Vérifiez que les drivers NVIDIA sont installés")
        print_info("Vérifiez que PyTorch CUDA est bien installé")
        return False


def test_memory_allocation():
    """Test l'allocation mémoire GPU"""
    print_header("Test Allocation Mémoire GPU")
    
    import torch
    
    try:
        # Alloue un tensor de test sur le GPU
        test_tensor = torch.randn(1000, 1000, device="cuda")
        print_success(f"Allocation réussie: tensor de forme {test_tensor.shape}")
        
        # Libère la mémoire
        del test_tensor
        torch.cuda.empty_cache()
        
        # Affiche l'état de la mémoire
        allocated = torch.cuda.memory_allocated() / 1024**2
        reserved = torch.cuda.memory_reserved() / 1024**2
        print_info(f"Mémoire allouée: {allocated:.1f} MB")
        print_info(f"Mémoire réservée: {reserved:.1f} MB")
        
        return True
    except Exception as e:
        print_error(f"Erreur d'allocation: {e}")
        return False


def test_float16_support():
    """Test le support Float16 (Half Precision)"""
    print_header("Test Float16 (Half Precision)")
    
    import torch
    
    try:
        # Crée un tensor en Float16
        tensor_fp16 = torch.randn(100, 100, dtype=torch.float16, device="cuda")
        
        # Effectue une opération
        result = torch.matmul(tensor_fp16, tensor_fp16.T)
        
        print_success(f"Float16 fonctionne correctement")
        print_info(f"Résultat shape: {result.shape}, dtype: {result.dtype}")
        
        del tensor_fp16, result
        torch.cuda.empty_cache()
        
        return True
    except Exception as e:
        print_error(f"Erreur Float16: {e}")
        return False


def test_transformers():
    """Test l'installation de Transformers"""
    print_header("Test Transformers")
    
    try:
        import transformers
        print_success(f"Transformers version: {transformers.__version__}")
        
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
        print_success("Imports critiques OK")
        
        return True
    except ImportError as e:
        print_error(f"Transformers non installé: {e}")
        return False


def test_audio():
    """Test les dépendances audio"""
    print_header("Test Audio (SoundDevice)")
    
    try:
        import sounddevice as sd
        print_success(f"SoundDevice version: {sd.__version__}")
        
        # Liste les périphériques audio
        devices = sd.query_devices()
        default_input = sd.query_devices(kind='input')
        
        print_info(f"Périphérique d'entrée par défaut: {default_input['name']}")
        print_info(f"Fréquences supportées: {default_input['default_samplerate']} Hz")
        
        return True
    except Exception as e:
        print_error(f"Erreur audio: {e}")
        return False


def main():
    """Exécute tous les tests"""
    print(f"\n{Fore.MAGENTA}{'#'*50}")
    print(f"#  WhisperFlow Desktop - Diagnostic GPU")
    print(f"{'#'*50}{Style.RESET_ALL}")
    
    results = []
    
    # Tests séquentiels
    results.append(("PyTorch", test_pytorch()))
    
    if results[-1][1]:  # Si PyTorch OK
        results.append(("CUDA", test_cuda()))
        
        if results[-1][1]:  # Si CUDA OK
            results.append(("Allocation Mémoire", test_memory_allocation()))
            results.append(("Float16", test_float16_support()))
    
    results.append(("Transformers", test_transformers()))
    results.append(("Audio", test_audio()))
    
    # Résumé
    print_header("RÉSUMÉ")
    
    all_passed = True
    for name, passed in results:
        if passed:
            print_success(f"{name}: OK")
        else:
            print_error(f"{name}: ÉCHEC")
            all_passed = False
    
    print()
    if all_passed:
        print(f"{Fore.GREEN}{'='*50}")
        print("  🚀 SYSTÈME PRÊT POUR WHISPERFLOW!")
        print(f"{'='*50}{Style.RESET_ALL}")
        return 0
    else:
        print(f"{Fore.RED}{'='*50}")
        print("  ⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print("  Corrigez les erreurs avant de lancer l'application")
        print(f"{'='*50}{Style.RESET_ALL}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
