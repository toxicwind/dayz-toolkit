import { XMLParser, XMLValidator } from 'fast-xml-parser';

export interface ValidationResult {
    valid: boolean;
    errors: string[];
    warnings: string[];
}

export function validateXml(xmlContent: string): ValidationResult {
    const result: ValidationResult = {
        valid: true,
        errors: [],
        warnings: []
    };

    if (!xmlContent || xmlContent.trim() === '') {
        result.valid = false;
        result.errors.push('XML content is empty');
        return result;
    }

    // Validate XML structure
    const validationResult = XMLValidator.validate(xmlContent, {
        allowBooleanAttributes: true
    });

    if (validationResult !== true) {
        result.valid = false;
        result.errors.push(`XML Syntax Error: ${validationResult.err.msg} at line ${validationResult.err.line}`);
        return result;
    }

    // Parse and check for common issues
    try {
        const parser = new XMLParser({
            ignoreAttributes: false,
            attributeNamePrefix: '@_'
        });
        const parsed = parser.parse(xmlContent);

        // Check for DayZ-specific patterns
        if (xmlContent.includes('cfgeconomycore')) {
            if (!xmlContent.includes('economycore')) {
                result.warnings.push('Economy core file missing root economycore element');
            }
        }

        if (xmlContent.includes('cfgeventspawns')) {
            if (!xmlContent.includes('eventposdef')) {
                result.warnings.push('Event spawns file should contain eventposdef elements');
            }
        }

        if (xmlContent.includes('cfgweather')) {
            if (!xmlContent.includes('weather')) {
                result.warnings.push('Weather file missing weather configuration');
            }
        }

        // Check for suspiciously large values
        const numericMatches = xmlContent.match(/>\s*(\d+)\s*</g);
        if (numericMatches) {
            numericMatches.forEach(match => {
                const value = parseInt(match.replace(/[><\s]/g, ''));
                if (value > 1000000) {
                    result.warnings.push(`Large numeric value detected: ${value} - verify this is intentional`);
                }
            });
        }

    } catch (e: any) {
        result.valid = false;
        result.errors.push(`Parse error: ${e.message}`);
    }

    return result;
}

export function getXmlStats(xmlContent: string) {
    const lines = xmlContent.split('\n').length;
    const elements = (xmlContent.match(/<[^/!?][^>]*>/g) || []).length;
    const attributes = (xmlContent.match(/\w+="[^"]*"/g) || []).length;
    const comments = (xmlContent.match(/<!--[\s\S]*?-->/g) || []).length;
    const size = new Blob([xmlContent]).size;

    return {
        lines,
        elements,
        attributes,
        comments,
        sizeBytes: size,
        sizeKb: (size / 1024).toFixed(2)
    };
}
