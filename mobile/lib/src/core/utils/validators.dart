class Validators {
  static String? validatePhone(String? value) {
    if (value == null || value.isEmpty) {
      return 'Phone number is required';
    }
    // Kenyan phone format: 07xx, 01xx, 7xx, 1xx (10 digits starting with 0, or 9 digits)
    final phoneRegex = RegExp(r'^(?:254|0|)([17]\d{8})$');
    if (!phoneRegex.hasMatch(value)) {
      return 'Enter a valid Kenyan phone number';
    }
    return null;
  }

  static String? validateNationalId(String? value) {
    if (value == null || value.isEmpty) {
      return 'National ID is required';
    }
    if (value.length < 6 || value.length > 9) {
      return 'National ID should be 6-9 digits';
    }
    if (int.tryParse(value) == null) {
      return 'Enter a valid numeric ID';
    }
    return null;
  }

  static String? validateAmount(String? value) {
    if (value == null || value.isEmpty) {
      return 'Amount is required';
    }
    final amount = double.tryParse(value);
    if (amount == null || amount < 300) {
      return 'Minimum contribution is KES 300';
    }
    return null;
  }
}
